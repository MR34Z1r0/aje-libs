# -*- coding: utf-8 -*-
import time
import pandas as pd
from typing import Optional, Tuple, Iterator, Dict, Any, TYPE_CHECKING
from datetime import datetime
from ...contracts.extractor_interface import IExtractor
from ....shared.models import DatabaseConfig  # ✅ Movido a shared/models
from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConnectionError,
    ProcessingError as ExtractionError,
)
# ✅ DIP: Usar interfaz en lugar de implementación concreta
if TYPE_CHECKING:
    from ....shared.contracts.secrets import ISecretProvider
else:
    ISecretProvider = None  # Para evitar importación circular

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    import pymssql

class SQLServerExtractor(IExtractor):
    """SQL Server implementation with SQLAlchemy support for better pandas compatibility"""
    
    def __init__(
        self, 
        config: DatabaseConfig, 
        secret_provider: Optional['ISecretProvider'] = None,  # ✅ DIP: Usar interfaz
        name_logger: Optional[str] = None
    ):
        """
        Inicializa el extractor de SQL Server
        
        Args:
            config: Configuración de base de datos
            secret_provider: Proveedor de secretos (opcional, se crea si no se proporciona)
            name_logger: Nombre del logger (opcional)
        """
        self.config = config
        self.connection = None
        self.engine = None
        self._password = None
        # ✅ Usar configuración centralizada en lugar de valores hardcodeados
        from ....shared.config import get_settings
        settings = get_settings()
        self.max_retries = settings.default_max_retries
        self.retry_delay = settings.default_retry_delay
        self.use_sqlalchemy = True  # Prefer SQLAlchemy when available

        from ....shared.services.logging import LoggerService
        self.logger = LoggerService.get_logger(name_logger or __name__)
        
        # ✅ DIP: Usar interfaz en lugar de implementación concreta
        # Si no se proporciona secret_provider, crear uno por defecto usando factory
        if secret_provider is None:
            from ....shared.factories import SecretProviderFactory
            # Obtener región de config si está disponible
            region = getattr(config, 'region', None)
            self._secret_provider = SecretProviderFactory.create(
                provider_type='aws_secrets_manager',
                region=region,
                logger_name=f"{__name__}.secrets"
            )
            self.logger.debug("✅ Secret provider creado automáticamente usando factory")
        else:
            self._secret_provider = secret_provider
            self.logger.debug("✅ Secret provider proporcionado externamente")
    
    def connect(self):
        """Establish connection using SQLAlchemy engine for better pandas compatibility"""
        try:
            if not self._password:
                self._get_password()
            
            if HAS_SQLALCHEMY and self.use_sqlalchemy:
                self._connect_sqlalchemy()
            else:
                self._connect_pymssql()
                
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQL Server: {e}")
    
    def _connect_sqlalchemy(self):
        """Connect using SQLAlchemy engine"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("ESTABLISHING DATABASE CONNECTION (SQLAlchemy)")
            self.logger.info("=" * 80)
            self.logger.info(f"Server: {self.config.server}")
            self.logger.info(f"Database: {self.config.database}")
            self.logger.info(f"User: {self.config.username}")
            self.logger.info(f"Port: {self.config.port or 1433}")
            
            # Create SQLAlchemy connection string
            connection_string = (
                f"mssql+pymssql://{self.config.username}:{self._password}"
                f"@{self.config.server}:{self.config.port or 1433}/{self.config.database}"
                f"?charset=utf8&timeout=900&login_timeout=900"
            )
            
            # Create engine with connection pooling
            self.engine = create_engine(
                connection_string,
                pool_size=3,
                max_overflow=5,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.logger.info("✅ SQLAlchemy engine connected successfully")
            self.logger.info(f"Connection pool size: 3, max overflow: 5")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.warning(f"❌ SQLAlchemy connection failed: {e}")
            self.logger.info("🔄 Falling back to pymssql...")
            self.use_sqlalchemy = False
            self._connect_pymssql()
    
    def _connect_pymssql(self):
        """Fallback to pymssql connection"""
        import pymssql
        
        # Agrupar información de conexión en un solo mensaje
        self.logger.info(
            f"🔌 Conectando a SQL Server (PyMSSQL) - "
            f"Server: {self.config.server}, Database: {self.config.database}, "
            f"User: {self.config.username}, Port: {self.config.port or 1433}"
        )
        
        self.connection = pymssql.connect(
            server=self.config.server,
            user=self.config.username,
            password=self._password,
            database=self.config.database,
            port=self.config.port or 1433,
            timeout=900,
            login_timeout=900,
            charset='utf8'
        )
        
        self.logger.info("✅ Conexión establecida exitosamente")
    
    def test_connection(self) -> bool:
        """Test connection to SQL Server"""
        try:
            if not self.connection and not self.engine:
                self.connect()
            
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1 as test"))
                self.logger.info("✅ Database connection test successful (SQLAlchemy)")
                return True
            else:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                cursor.close()
                self.logger.info("✅ Database connection test successful (PyMSSQL)")
                return result is not None
                
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute query with retry logic and better error handling"""
        for attempt in range(self.max_retries):
            try:
                if not self.connection and not self.engine:
                    self.connect()
                
                # Mostrar query ANTES de ejecutarse para validación
                if attempt == 0:
                    self.logger.info(f"📝 SQL Query a ejecutar:\n{query}")
                else:
                    self.logger.info(f"🔄 Reintentando query (intento {attempt + 1}/{self.max_retries})")
                    self.logger.info(f"📝 SQL Query:\n{query}")
                
                start_time = datetime.now()
                
                if self.engine:
                    # Use SQLAlchemy engine
                    if params:
                        df = pd.read_sql(text(query), self.engine, params=params)
                    else:
                        df = pd.read_sql(text(query), self.engine)
                else:
                    # Use pymssql connection
                    if params:
                        df = pd.read_sql(query, self.connection, params=params)
                    else:
                        df = pd.read_sql(query, self.connection)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Fix duplicate column names
                df = self._fix_duplicate_columns(df)
                
                # Agrupar resultados de query en un solo mensaje
                self.logger.info(
                    f"✅ Query ejecutada exitosamente - "
                    f"Tiempo: {duration:.2f}s, Filas: {len(df):,}, Columnas: {len(df.columns)}"
                )
                
                return df
                
            except Exception as e:
                self.logger.error(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    self.logger.info(f"⏳ Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    
                    # Recreate connection on retry
                    try:
                        self.close()
                        self.connect()
                    except:
                        pass
                else:
                    self.logger.error(f"❌ All {self.max_retries} attempts failed")
                    raise ExtractionError(f"Failed to execute query after {self.max_retries} attempts: {e}")
    
    def execute_query_chunked(self, query: str, chunk_size: int, order_by: str, params: Optional[Tuple] = None) -> Iterator[pd.DataFrame]:
        """Execute query in chunks using OFFSET/FETCH"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("CHUNKED QUERY EXECUTION")
            self.logger.info("=" * 80)
            self.logger.info(f"Chunk size: {chunk_size:,}")
            self.logger.info(f"Order by: {order_by}")
            
            offset = 0
            chunk_number = 0
            
            while True:
                chunk_number += 1
                
                # Build chunked query
                chunked_query = f"""
                {query}
                ORDER BY {order_by}
                OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY
                """
                
                self.logger.info("-" * 80)
                self.logger.info(f"Chunk #{chunk_number}: offset={offset:,}, size={chunk_size:,}")
                self.logger.info("SQL Query:")
                self.logger.info(chunked_query)
                self.logger.info("-" * 80)
                
                # Execute chunk query
                chunk_df = self.execute_query(chunked_query, params)
                
                self.logger.info(f"Chunk #{chunk_number} returned {len(chunk_df):,} rows")
                
                if chunk_df.empty:
                    self.logger.info(f"Empty chunk received, stopping pagination")
                    break
                    
                yield chunk_df
                
                # If we got fewer rows than chunk_size, we've reached the end
                if len(chunk_df) < chunk_size:
                    self.logger.info(f"Last chunk received ({len(chunk_df):,} < {chunk_size:,}), stopping pagination")
                    break
                    
                offset += chunk_size
            
            self.logger.info("=" * 80)
            self.logger.info(f"CHUNKED EXECUTION COMPLETED - Total chunks: {chunk_number}")
            self.logger.info("=" * 80)
                
        except Exception as e:
            self.logger.error(f"❌ Chunked extraction failed: {e}")
            raise ExtractionError(f"Failed chunked extraction: {e}")
    
    def extract_data(self, query: str, chunk_size: Optional[int] = None, 
                 order_by: Optional[str] = None, 
                 params: Optional[Tuple] = None) -> Iterator[pd.DataFrame]:
        """
        Extract data using query - main extraction method
        """
        try:
            if chunk_size and order_by:
                # Agrupar información de extracción chunked
                self.logger.info(
                    f"📊 Iniciando extracción CHUNKED - "
                    f"Chunk size: {chunk_size:,}, Order by: {order_by}"
                )
                self.logger.debug(f"SQL Query: {query}")
                
                # Use chunked extraction
                chunk_count = 0
                for chunk_df in self.execute_query_chunked(query, chunk_size, order_by, params):
                    chunk_count += 1
                    self.logger.debug(f"Chunk {chunk_count}: {len(chunk_df):,} filas")
                    yield chunk_df
                
                self.logger.info(f"✅ Extracción chunked completada - Total chunks: {chunk_count}")
            else:
                # Agrupar información de extracción simple
                self.logger.info("📊 Iniciando extracción SINGLE QUERY")
                self.logger.debug(f"SQL Query: {query}")
                
                df = self.execute_query(query, params)
                
                if not df.empty:
                    self.logger.debug(f"Resultado: {len(df):,} filas")
                    yield df
                else:
                    self.logger.warning("⚠️ Query retornó resultado vacío")
            
            self.logger.info("✅ Extracción de datos completada")
                    
        except Exception as e:
            self.logger.error(f"❌ Error en extracción de datos: {type(e).__name__} - {str(e)}")
            
            import traceback
            self.logger.error("Traceback:")
            self.logger.error(traceback.format_exc())
            self.logger.error("=" * 80)
            
            raise ExtractionError(f"Failed to extract data: {e}")
    
    def get_min_max_values(self, query: str) -> Tuple[Optional[int], Optional[int]]:
        """Get min and max values from query"""
        try:
            self.logger.info("Executing MIN/MAX query")
            df = self.execute_query(query)
            
            if df.empty:
                self.logger.warning("MIN/MAX query returned empty result")
                return None, None
            
            min_val = df.iloc[0]['min_val'] if 'min_val' in df.columns else None
            max_val = df.iloc[0]['max_val'] if 'max_val' in df.columns else None
            
            min_val = int(min_val) if min_val is not None else None
            max_val = int(max_val) if max_val is not None else None
            
            self.logger.info(f"MIN/MAX values: min={min_val}, max={max_val}")
            
            return min_val, max_val
            
        except Exception as e:
            self.logger.error(f"Failed to get MIN/MAX values: {e}")
            raise ExtractionError(f"Failed to get min/max values: {e}")
    
    def close(self):
        """Close connections"""
        if self.engine:
            try:
                self.engine.dispose()
                self.logger.info("🔒 SQLAlchemy engine disposed")
            except Exception:
                pass
            finally:
                self.engine = None
                
        if self.connection:
            try:
                self.connection.close()
                self.logger.info("🔒 PyMSSQL connection closed")
            except Exception:
                pass
            finally:
                self.connection = None
    
    def _get_password(self):
        """Get password from secrets provider (DIP - usa interfaz, no implementación concreta)"""
        if not self._password:
            secret_name = self.config.secret_name.lower() if self.config.secret_name else ""
            secret_key = self.config.secret_key or 'password'
            
            if not secret_name:
                raise ConnectionError("secret_name no está configurado en DatabaseConfig")
            
            # ✅ Seguridad: Solo loguear información no sensible
            self.logger.debug(f"Obteniendo secreto: {secret_name}, clave: {secret_key}")
            # ✅ DIP: Usar interfaz ISecretProvider en lugar de SecretsHelper concreta
            self._password = self._secret_provider.get_secret_value(secret_name, secret_key)
            
            if not self._password:
                raise ConnectionError(f"No se pudo obtener el secreto '{secret_key}' de '{secret_name}'")
            
            # ✅ Seguridad: No loguear el password obtenido
            self.logger.debug(f"✅ Secreto obtenido exitosamente de '{secret_name}' (clave: {secret_key})")
    
    def _fix_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix duplicate column names"""
        if df.empty:
            return df
        
        columns = list(df.columns)
        if len(columns) != len(set(columns)):
            seen = {}
            new_columns = []
            
            for col in columns:
                if col in seen:
                    seen[col] += 1
                    new_col = f"{col}_{seen[col]}"
                else:
                    seen[col] = 0
                    new_col = col
                new_columns.append(new_col)
            
            df.columns = new_columns
        
        return df