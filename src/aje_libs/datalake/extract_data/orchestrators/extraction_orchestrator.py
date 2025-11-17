# -*- coding: utf-8 -*-
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from ..models.extraction_config import ExtractionConfig
from ..models.extraction_result import ExtractionResult
from ..contracts.extractor_interface import IExtractor
from aje_libs.datalake.shared.models import LoadMode, TableConfig, DatabaseConfig  # ✅ DatabaseConfig movido a shared/models 
from ..contracts.loader_interface import ILoader
from ...shared.contracts.monitoring import IMonitor
from ..contracts.strategy_interface import IExtractionStrategy
from ...shared.contracts.watermark import IWatermarkStorage
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...shared.contracts.factories import IComponentFactory  # ✅ Nueva interfaz (import diferido para evitar circular)
from ...shared.contracts.configuration import IConfigurationProvider
from ..factories.extraction_component_factory import DefaultComponentFactory  # ✅ Nueva factory
from ..orchestrators.component_initializer import ComponentInitializer  # ✅ Nuevo inicializador
from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConfigurationError,
    ProcessingError as ExtractionError,
)
from ...shared.utils.partition_formatter import PartitionFormatter
from ...shared.builders import DatabaseConfigBuilder  # ✅ Builder para configs

class DataExtractionOrchestrator:
    """Main orchestrator for the data extraction process"""
    
    def __init__(
        self,
        extraction_config: ExtractionConfig,
        monitor: IMonitor = None,
        process_guid: str = None,
        configuration_provider: IConfigurationProvider = None,
               component_factory: Optional['IComponentFactory'] = None,  # ✅ Nueva inyección de dependencias
    ):
        self.extraction_config = extraction_config
        self.monitor = monitor  # Recibir monitor desde main
        self.process_guid = process_guid
        self.table_config: Optional[TableConfig] = None
        self.database_config: Optional[DatabaseConfig] = None
        
        # ✅ Inyección de dependencias: usar factory proporcionado o crear uno por defecto
        self.component_factory = component_factory or DefaultComponentFactory(name_logger=f"{__name__}.factory")
        
        # Inicializar logger - AGREGAR ESTA LÍNEA
        from ...shared.services.logging import LoggerService
        self.logger = LoggerService.get_logger(__name__)
        
        # Definir name_logger para usar en extractor factory
        self.name_logger = f"{__name__}.extractor"
        
        if self.process_guid:
            self.logger.debug(f"Orchestrator inicializado - process_guid: {self.process_guid}")
        
        # Components
        self.extractor: Optional[IExtractor] = None
        self.loader: Optional[ILoader] = None
        self.monitor: Optional[IMonitor] = None
        self.strategy: Optional[IExtractionStrategy] = None
        self.watermark_storage: Optional[IWatermarkStorage] = None
        self.configuration_provider = configuration_provider
        
        # Results tracking
        self.extraction_result: Optional[ExtractionResult] = None
        
    def execute(self) -> ExtractionResult:
        """Execute the complete data extraction process"""
        start_time = datetime.now()
        
        try:
            # Initialize all components
            self._initialize_components()
            
            # Agrupar información de inicio
            self.logger.info(
                f"🚀 Iniciando extracción - "
                f"Tabla: {self.extraction_config.table_name}, "
                f"Mode: {self.extraction_config.load_mode.value}, "
                f"Process GUID: {self.process_guid}"
            )
            
            # 🧹 RESET MODE: Ejecutar cleanup ANTES de log_start
            if self.extraction_config.load_mode == LoadMode.RESET:
                cleanup_result = self._execute_reset_cleanup()
                
                if not cleanup_result.get('success', False):
                    error_msg = (
                        f"Error durante limpieza RESET: {cleanup_result.get('details', 'Unknown error')}. "
                        f"Errores: {cleanup_result.get('errors', [])}"
                    )
                    self.logger.error(error_msg)
                    self.logger.warning("Continuando con extracción después de errores en cleanup")
                # El log de éxito ya se muestra en _execute_reset_cleanup(), no duplicar aquí
            
            # ✅ Log start DESPUÉS de que el cleanup se complete (en modo RESET)
            # o inmediatamente (en otros modos)
            start_metadata = self._build_metadata()
            start_metadata.update({
                'load_mode': self.extraction_config.load_mode.value,
                'strategy': self.strategy.get_strategy_name(),
            })
            self.monitor.log_start(
                self.extraction_config.table_name,
                self.strategy.get_strategy_name(),
                start_metadata
            )
            
            # Validate configuration
            self._validate_configuration()
            
            # Execute extraction strategy
            extraction_result = self._execute_extraction_strategy()
            
            # Log success with enriched metadata
            if self.monitor:
                success_metadata = (extraction_result.metadata or {}).copy()
                success_metadata.update({
                    'records_extracted': extraction_result.records_extracted,
                    'files_created': extraction_result.files_created,
                    'execution_time_seconds': extraction_result.execution_time_seconds,
                    'files_count': len(extraction_result.files_created),
                    'files_metadata': extraction_result.files_metadata,
                    'start_time': extraction_result.start_time.isoformat() if extraction_result.start_time else None,
                    'end_time': extraction_result.end_time.isoformat() if extraction_result.end_time else None,
                    'total_size_mb': float(extraction_result.get_total_size_mb()) if extraction_result.files_metadata else 0,
                    'average_file_size_mb': float(extraction_result.get_average_file_size_mb()) if extraction_result.files_metadata else 0,
                    'strategy': extraction_result.strategy_used,
                    'load_mode': self.extraction_config.load_mode.value,
                    'success': extraction_result.success,
                })
                
                if extraction_result.records_extracted > 0:
                    self.monitor.log_success(
                        table_name=extraction_result.table_name,
                        job_name=f"extract_{extraction_result.strategy_used}",
                        metadata=success_metadata
                    )
                elif extraction_result.records_extracted == 0:
                    # Ya se registró como warning en _execute_extraction_strategy, pero registramos también como success con 0 records
                    self.monitor.log_success(
                        table_name=extraction_result.table_name,
                        job_name=f"extract_{extraction_result.strategy_used}",
                        metadata=success_metadata
                    )
            
            return extraction_result
            
        except Exception as e:
            error_message = f"Extraction failed: {str(e)}"
            
            self.logger.error(
                f"❌ {error_message} "
                f"table: {self.extraction_config.table_name} "
                f"process_guid: {self.process_guid}",
                exc_info=True
            )
            
            # Log error
            if self.monitor:
                strategy_name = self.strategy.get_strategy_name() if self.strategy else "unknown"
                error_metadata = self._build_metadata()
                error_metadata.update({
                    'error_type': type(e).__name__,
                    'traceback': str(e),
                    'strategy': strategy_name,
                    'load_mode': self.extraction_config.load_mode.value,
                })
                self.monitor.log_error(
                    table_name=self.extraction_config.table_name,
                    error_message=error_message,
                    job_name=f"extract_{strategy_name}",
                    metadata=error_metadata
                )
                # Note: log_error already sends notifications via notification_service
            
            # Create error result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            error_result = ExtractionResult(
                success=False,
                table_name=self.extraction_config.table_name,
                records_extracted=0,
                files_created=[],
                execution_time_seconds=execution_time,
                strategy_used=self.strategy.get_strategy_name() if self.strategy else "unknown",
                error_message=error_message,
                start_time=start_time,
                end_time=end_time
            )
            
            raise ExtractionError(error_message) from e
            
        finally:
            # Cleanup resources
            self._cleanup()
    
    def _initialize_components(self):
        """
        Initialize all components needed for extraction (SRP - delega a ComponentInitializer)
        """
        # ✅ Usar ComponentInitializer para inicializar componentes (SRP - separación de responsabilidades)
        initializer = ComponentInitializer(
            config=self.extraction_config,
            component_factory=self.component_factory,
            logger=self.logger
        )
        
        # Inicializar todos los componentes
        components = initializer.initialize_all(
            configuration_provider=self.configuration_provider,
            monitor=self.monitor,
            process_guid=self.process_guid
        )
        
        # Asignar componentes inicializados
        self.extractor = components['extractor']
        self.loader = components['loader']
        self.monitor = components['monitor'] or self.monitor  # Mantener el monitor proporcionado si existe
        self.watermark_storage = components['watermark_storage']
        self.strategy = components['strategy']
        self.configuration_provider = components['configuration_provider']
        self.table_config = components['table_config']
        self.database_config = components['database_config'] 
    
    def _strategy_needs_watermark_storage(self) -> bool:
        """Determina si la estrategia necesita watermark storage"""
        
        # Solo las estrategias incrementales necesitan watermarks
        load_type = self.table_config.load_type.lower().strip() if self.table_config.load_type else 'full'
        
        incremental_types = ['incremental']
        
        if load_type in incremental_types:
            # Verificar que tenga los campos necesarios para incremental con watermarks
            has_partition_column = (
                hasattr(self.table_config, 'partition_column') and 
                self.table_config.partition_column and 
                self.table_config.partition_column.strip()
            )
            
            return has_partition_column
        
        return False

    def _load_configurations(self):
        """Load table and database configurations from the provider"""
        try:
            # Usar config_sources (Dict[str, ResourceRef])
            tables_ref = self.extraction_config.config_sources.get("tables") if self.extraction_config.config_sources else None
            credentials_ref = self.extraction_config.config_sources.get("credentials") if self.extraction_config.config_sources else None
            columns_ref = self.extraction_config.config_sources.get("columns") if self.extraction_config.config_sources else None
            
            # Usar config_sources de ExtractionConfig, sin fallback a variables de entorno
            if not tables_ref:
                raise ConfigurationError(
                    "config_sources['tables'] debe estar configurado en ExtractionConfig. "
                    "No se pueden usar variables de entorno como fallback."
                )
            tables_source = tables_ref.location
            
            credentials_source = credentials_ref.location if credentials_ref else None
            columns_source = columns_ref.location if columns_ref else None

            self.logger.debug(f"📂 Cargando configuración de tabla desde: {tables_source}")
            table_row = self.configuration_provider.get_table_config(
                self.extraction_config.table_name, tables_source
            )
            
            self.logger.debug(f"🔐 Cargando configuración de endpoint desde: {credentials_source}")
            db_row = self.configuration_provider.get_endpoint_config(
                self.extraction_config.endpoint_name,
                credentials_source,
                ENV=self.extraction_config.environment,
            )
            
            self.logger.debug(f"📊 Cargando metadata de columnas desde: {columns_source}")
            columns_data = self.configuration_provider.get_columns_metadata(
                self.extraction_config.table_name,
                columns_source,
            )

            self.table_config = self._build_table_config(table_row)
            self.database_config = self._build_database_config(db_row)
            
            self.logger.debug(f"✅ Tabla configurada: {self.table_config.source_schema}.{self.table_config.source_table}")
            self.logger.debug(f"✅ Endpoint configurado: {self.database_config.endpoint_name} ({self.database_config.db_type})")

            if self.table_config and hasattr(self.table_config, 'partition_format'):
                partition_format = self.table_config.partition_format
                self.partition_formatter = PartitionFormatter(partition_format)
                self.logger.debug(f"📅 Formato de partición cargado: {partition_format}")
            else:
                self.partition_formatter = PartitionFormatter()
                self.logger.debug("📅 Usando formato de partición por defecto")

        except Exception as e:
            self.logger.error(f"❌ Error cargando configuraciones: {e}", exc_info=True)
            raise ConfigurationError(f"Failed to load configurations: {e}")
    
    def _build_table_config(self, table_row: Dict[str, Any]) -> TableConfig:
        """Build TableConfig from CSV row""" 
        
        # Apply load type logic - default to 'full' if not explicitly set
        load_type = table_row.get('LOAD_TYPE', '').strip()
        
        if not load_type:
            load_type = 'full'
        
        self.logger.debug(f"Table config - load_type: '{load_type}'")
        
        return TableConfig(
            stage_table_name=table_row.get('STAGE_TABLE_NAME', ''),
            source_schema=table_row.get('SOURCE_SCHEMA', ''),
            source_table=table_row.get('SOURCE_TABLE', ''),
            columns=self._process_columns_field(table_row.get('COLUMNS', '')),
            load_type=load_type,
            source_table_type=table_row.get('SOURCE_TABLE_TYPE', ''),
            partition_mode=table_row.get('PARTITION_MODE', 'AUTO'),
            partition_format=table_row.get('PARTITION_FORMAT'),
            id_column=table_row.get('ID_COLUMN'),
            partition_column=table_row.get('PARTITION_COLUMN'),
            filter_exp=table_row.get('FILTER_EXP'),
            filter_column=table_row.get('FILTER_COLUMN'),
            filter_data_type=table_row.get('FILTER_DATA_TYPE'),
            join_expr=table_row.get('JOIN_EXPR'),
            delay_incremental_ini=table_row.get('DELAY_INCREMENTAL_INI'),
            delay_incremental_end=table_row.get('DELAY_INCREMENTAL_END'),
            start_value=table_row.get('START_VALUE'),
            end_value=table_row.get('END_VALUE')
        )
    
    def _build_database_config(self, db_row: Dict[str, Any]) -> DatabaseConfig:
        """
        Build DatabaseConfig from CSV row (usando Builder Pattern)
        
        Args:
            db_row: Diccionario con los datos de la fila CSV
            
        Returns:
            DatabaseConfig configurada
        """
        # Construir el nombre del secreto basado en la configuración de extracción
        secret_name = f"{self.extraction_config.environment.lower()}/{self.extraction_config.project_name}/{self.extraction_config.team}/{self.extraction_config.data_source}"
        
        # ✅ Usar DatabaseConfigBuilder para construcción más clara y mantenible
        builder = DatabaseConfigBuilder.create()
        
        # Mapear campos del CSV al builder
        db_row_mapped = {
            'ENDPOINT_NAME': db_row.get('ENDPOINT_NAME', ''),
            'BD_TYPE': db_row.get('BD_TYPE', ''),
            'SRC_SERVER_NAME': db_row.get('SRC_SERVER_NAME', ''),
            'SRC_DB_NAME': db_row.get('SRC_DB_NAME', ''),
            'SRC_DB_USERNAME': db_row.get('SRC_DB_USERNAME', ''),
            'SRC_DB_SECRET': db_row.get('SRC_DB_SECRET', ''),
            'DB_PORT_NUMBER': db_row.get('DB_PORT_NUMBER'),
            'SECRET_NAME': secret_name,
            'SECRET_KEY': db_row.get('SRC_DB_SECRET', ''),
        }
        
        return builder.from_dict(db_row_mapped).build()
    
    def _build_watermark_storage_config(self) -> Optional[Dict[str, Any]]:
        """
        Build watermark storage configuration from ExtractionConfig.
        Usa watermark_storage ResourceRef si está disponible, de lo contrario retorna None.
        """
        if not self.extraction_config.watermark_storage:
            return None
        
        watermark_ref = self.extraction_config.watermark_storage
        storage_type = watermark_ref.provider.lower()
        
        config = {
            'storage_type': storage_type,
            'project_name': self.extraction_config.project_name,
            'team': self.extraction_config.team,
            'data_source': self.extraction_config.data_source,
            'endpoint_name': self.database_config.endpoint_name if hasattr(self, 'database_config') and self.database_config else ''
        }
        
        if storage_type == 'dynamodb':
            # Para DynamoDB, la location es el nombre de la tabla
            config['table_name'] = watermark_ref.location or 'extraction-watermarks'
            # Agregar opciones si existen
            config.update(watermark_ref.options)
        elif storage_type == 'csv':
            # Para CSV, la location es la ruta del archivo
            config['csv_file_path'] = watermark_ref.location or './data/watermarks.csv'
            # Agregar opciones si existen
            config.update(watermark_ref.options)
        else:
            # Para otros tipos, usar location y options directamente
            if watermark_ref.location:
                config['location'] = watermark_ref.location
            config.update(watermark_ref.options)
        
        return config
    
    def _process_columns_field(self, columns_str: str) -> str:
        """Process columns field to handle SQL Server identifier issues"""
        if not columns_str or columns_str.strip() == '':
            return columns_str
            
        # Clean problematic double quotes
        clean_columns = columns_str.strip()
        
        # Remove wrapping quotes or all quotes
        double_quote_count = clean_columns.count('"')
        if double_quote_count > 0:
            if clean_columns.startswith('"') and clean_columns.endswith('"') and double_quote_count == 2:
                clean_columns = clean_columns[1:-1]
            else:
                clean_columns = clean_columns.replace('"', '')
        
        return clean_columns
    
    def _build_loader_config(self) -> Dict[str, Any]:
        """Build loader configuration from ExtractionConfig"""
        config = {}
        
        if self.extraction_config.raw_storage:
            config['bucket_name'] = self.extraction_config.raw_storage.location
            config['region'] = self.extraction_config.raw_storage.options.get('region')
            # Agregar configuración adicional si existe
            config.update(self.extraction_config.raw_storage.options)
        else:
            # Si no hay raw_storage config, lanzar error en lugar de usar fallback a variables de entorno
            raise ConfigurationError(
                "raw_storage debe estar configurado en ExtractionConfig. "
                "No se pueden usar variables de entorno como fallback."
            )
        
        return config
    
    def _build_monitor_config(self) -> Dict[str, Any]:
        """
        Build monitor configuration from ExtractionConfig.
        Este método ya no es necesario porque el monitor se crea directamente desde ExtractionConfig,
        pero lo mantenemos por compatibilidad si se usa en otros lugares.
        """
        config = {}
        
        if self.extraction_config.monitoring:
            config['monitor_type'] = self.extraction_config.monitoring.provider.lower()
            config['table_name'] = self.extraction_config.monitoring.location
            config['project_name'] = self.extraction_config.project_name
            # ✅ Obtener ARN de 'failed' desde notification_targets o notification_target (compatibilidad)
            if self.extraction_config.notification_targets:
                failed_target = self.extraction_config.notification_targets.get('failed')
                config['sns_topic_arn'] = failed_target.location if failed_target else None
            elif self.extraction_config.notification_target:
                config['sns_topic_arn'] = self.extraction_config.notification_target.location
            else:
                config['sns_topic_arn'] = None
        else:
            # Si no hay monitoring config, no podemos crear un monitor válido
            # Esto es manejado en _initialize_components donde se verifica si hay monitor
            pass

        return config
    
    def _validate_configuration(self):
        """Validate all configurations"""
        
        try:
            if not self.strategy.validate_config():
                self.logger.error("❌ Strategy validation failed")
                raise ConfigurationError("Invalid strategy configuration")
            # Validación exitosa - no loguear, es el caso normal
        except Exception as e:
            self.logger.error(f"Error during strategy validation: {str(e)}")
            raise
    
    def _execute_extraction_strategy(self) -> ExtractionResult:
        """Execute the selected extraction strategy"""
        start_time = datetime.now()
        strategy_name = self.strategy.get_strategy_name()
        
        # Get destination path
        destination_path = self._build_destination_path()
        
        # Delete existing files for strategies that require it
        if self.extraction_config.load_mode in [LoadMode.INITIAL, LoadMode.RESET]:
            self.logger.debug(f"Eliminando archivos existentes para estrategia {strategy_name}")
            self.loader.delete_existing(destination_path)
        
        # 🔧 FIX: Generate queries based on strategy
        queries = self.strategy.generate_queries()
        
        if not queries:
            raise ExtractionError("No queries generated by strategy")
        
        # Execute queries with controlled concurrency
        files_created, files_metadata, total_records = self._execute_queries_parallel(queries)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        if total_records == 0:
            self.logger.warning(f"⚠️ No records extracted for table {self.extraction_config.table_name}")
            
            if self.monitor:
                strategy_name = self.strategy.get_strategy_name()
                warning_metadata = self._build_metadata()
                warning_metadata.update({
                    'records_extracted': 0,
                    'files_created': [],
                    'strategy': strategy_name,
                    'load_mode': self.extraction_config.load_mode.value,
                })
                self.monitor.log_warning(
                    table_name=self.extraction_config.table_name,
                    warning_message="No data extracted - Table is empty or no records match filter criteria",
                    job_name=f"extract_{strategy_name}",
                    metadata=warning_metadata
                )
        
        # Create result with enriched metadata
        result = ExtractionResult(
            success=True,
            table_name=self.extraction_config.table_name,
            records_extracted=total_records,
            files_created=files_created,
            execution_time_seconds=execution_time,
            strategy_used=self.strategy.get_strategy_name(),
            metadata=self._build_metadata(),
            start_time=start_time,
            end_time=end_time,
            files_metadata=files_metadata
        )
        
        # Log with aggregated metrics
        if files_metadata:
            total_size = sum(f.get('file_size_mb', 0) for f in files_metadata)
            avg_size = total_size / len(files_metadata) if files_metadata else 0
            
            self.logger.info(
                f"📊 Extraction Summary - "
                f"Files: {len(files_created)}, "
                f"Total Size: {total_size:.2f}MB, "
                f"Avg Size: {avg_size:.2f}MB"
            )
        
        self.extraction_result = result
        return result
    
    def _execute_queries_parallel(self, queries: List[Dict[str, Any]]) -> tuple:
        """Execute queries with controlled parallel processing"""
        max_workers = min(self.extraction_config.max_threads, len(queries))
        files_created = []
        all_files_metadata = []  # 🆕 Agregar lista para metadata
        total_records = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_query = {
                executor.submit(self._execute_single_query, i, query): query
                for i, query in enumerate(queries)
            }
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    # 🔧 FIX: Ahora recibe 3 valores
                    query_files, query_metadata, record_count = future.result()
                    
                    if query_files:
                        if isinstance(query_files, list):
                            files_created.extend(query_files)
                        else:
                            files_created.append(query_files)
                    
                    # 🆕 Agregar metadata
                    if query_metadata:
                        if isinstance(query_metadata, list):
                            all_files_metadata.extend(query_metadata)
                        else:
                            all_files_metadata.append(query_metadata)
                            
                    total_records += record_count
                except Exception as e:
                    raise ExtractionError(f"Failed to execute query: {e}")
        
        # Handle empty result case
        if total_records == 0:
            empty_files, empty_records = self._handle_empty_result()
            files_created = empty_files
            total_records = empty_records
        
        return files_created, all_files_metadata, total_records
    
    def _execute_single_query(self, thread_id: int, query_metadata: Dict[str, Any]) -> tuple:
        """Execute a single query and load the data"""
        query = query_metadata['query']
        metadata = query_metadata.get('metadata', {})
        
        # Agrupar información de thread y estrategia en un solo mensaje
        strategy_name = self.strategy.get_strategy_name()
        self.logger.info(
            f"🔍 Thread {thread_id} - Ejecutando query ({strategy_name}) - "
            f"process_guid: {self.process_guid}"
        )
        
        # Mostrar query ANTES de ejecutarse para validación
        self.logger.info(f"📝 SQL Query (Thread {thread_id}):\n{query}")
        
        if metadata.get('query_type') == 'min_max' and metadata.get('needs_partitioned_queries'):
            return self._handle_min_max_query(query, metadata)  # Ya retorna 3 valores

        files_created = []
        files_metadata = []
        total_records = 0
        max_extracted_value = None
        
        try:         
            # Extract data parameters
            chunk_size = metadata.get('chunk_size', self.extraction_config.chunk_size)
            chunking_params = metadata.get('chunking_params', {})
            order_by = chunking_params.get('order_by')

            # Debug info solo en modo DEBUG
            self.logger.debug(f"Partition column: '{self.table_config.partition_column}'")
            self.logger.debug(f"Watermark storage available: {self.watermark_storage is not None}")
            self.logger.debug(f"Chunk size: {chunk_size}, Order by: {order_by}, Chunking params: {chunking_params}")

            data_iterator = self.extractor.extract_data(query, chunk_size, order_by)
            destination_path = metadata.get('destination_path', self._build_destination_path())

            chunk_count = 0
            for chunk_df in data_iterator:
                if chunk_df is not None and not chunk_df.empty:
                    chunk_count += 1
                    # Solo loguear cada 10 chunks o el primero para no saturar logs
                    if chunk_count == 1 or chunk_count % 10 == 0:
                        self.logger.debug(f"Chunk {chunk_count}: {len(chunk_df)} filas")
                    
                    # 🎯 ACTUALIZAR MAX VALUE (para watermark)
                    if (self.table_config.partition_column and 
                        self.table_config.partition_column in chunk_df.columns):                        
                        chunk_max = chunk_df[self.table_config.partition_column].max()
                        if max_extracted_value is None or chunk_max > max_extracted_value:
                            max_extracted_value = chunk_max
                            self.logger.debug(f"Max value actualizado: {max_extracted_value}")
                    
                    # ✅ CARGAR CHUNK UNA SOLA VEZ
                    file_path = self.loader.load_dataframe(
                        chunk_df, 
                        destination_path, 
                        thread_id=f"{thread_id}_{chunk_count}"
                    )
                    
                    if file_path:
                        files_created.append(file_path)
                    
                    total_records += len(chunk_df)
                    chunk_count += 1
            
            # 🎯 CONFIRMAR WATERMARK (si aplica)
            strategy_name = self.strategy.get_strategy_name().lower()
            is_incremental = strategy_name in ['incremental', 'incrementalstrategy']
            should_track = metadata.get('should_track_watermark', False)
            
            self.logger.debug(f"is_incremental: {is_incremental}, should_track: {should_track}")
            
            if (max_extracted_value is not None and 
                self.watermark_storage and 
                self.table_config.partition_column and
                (is_incremental or should_track)):
                
                # Guardar watermark como PENDING (se confirmará después de transformación exitosa en light_transform)
                if hasattr(self.watermark_storage, 'save_provisional'):                    
                    # Guardar como PENDING - será confirmado por light_transform después de transformación exitosa
                    success = self.watermark_storage.save_provisional(
                        table_name=self.table_config.stage_table_name,
                        column_name=self.table_config.partition_column,
                        value=str(max_extracted_value),
                        metadata={
                            'thread_id': thread_id,
                            'strategy': self.strategy.get_strategy_name(),
                            'load_mode': self.extraction_config.load_mode.value,
                            'records_extracted': total_records,
                            'files_created': len(files_created)
                        }
                    )
                    if success:
                        self.logger.info(
                            f"✅ Watermark guardado como PENDING: {max_extracted_value} "
                            f"(será confirmado después de transformación exitosa en light_transform)"
                        )
                else:
                    # Método directo si no soporta transacciones
                    self.watermark_storage.update_last_extracted_value(
                        table_name=self.table_config.stage_table_name,
                        column_name=self.table_config.partition_column,
                        value=str(max_extracted_value)
                    )
                    self.logger.info(f"✅ Watermark saved: {max_extracted_value}")
            else:
                self.logger.debug("No watermark to save")
            
            return files_created, files_metadata, total_records
            
        except Exception as e:
            self.logger.error(f"❌ Error in query execution: {e}")
            raise ExtractionError(f"Failed to execute query for thread {thread_id}: {e}")
    
    def _handle_min_max_query(self, min_max_query: str, metadata: Dict[str, Any]) -> tuple:
        """Maneja la ejecución de query MIN/MAX y genera queries particionadas"""
        self.logger.info("🔍 Ejecutando query MIN/MAX para carga particionada")
        
        # Mostrar query MIN/MAX ANTES de ejecutarse para validación
        self.logger.info(f"📝 SQL Query MIN/MAX:\n{min_max_query}")
        
        try:
            # 1. Ejecutar query MIN/MAX
            df_results = []
            for chunk_df in self.extractor.extract_data(min_max_query):
                df_results.append(chunk_df)
            
            if not df_results or df_results[0].empty:
                self.logger.warning(f"⚠️ MIN/MAX query returned no results. Skipping table.")
                # Retornar resultado vacío pero válido
                return [], [],0
            
            # 2. Extraer valores MIN/MAX
            df = df_results[0]
            min_val = df['min_val'].iloc[0]
            max_val = df['max_val'].iloc[0]
            
            if min_val is None or max_val is None:
                self.logger.warning(f"⚠️ No valid data found for partitioning (MIN/MAX returned None). Skipping table.")
                # Retornar resultado vacío pero válido
                return [], [],0

            min_val = int(min_val)
            max_val = int(max_val)
            
            self.logger.info(f"🔍 MIN/MAX results: min={min_val}, max={max_val}")
            
            # 3. Generar queries particionadas
            partitioned_queries = self._generate_partitioned_queries(min_val, max_val, metadata)
            
            # 4. Ejecutar queries particionadas en paralelo
            files_created, files_metadata, total_records = self._execute_partitioned_queries(partitioned_queries)
            return files_created, files_metadata, total_records  # 🔧 Retornar 3 valores
            
        except Exception as e:
            raise ExtractionError(f"Failed to handle MIN/MAX query: {e}")
    
    def _generate_partitioned_queries(self, min_val: int, max_val: int, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera queries particionadas basadas en los valores MIN/MAX"""
        partition_column = metadata['partition_column']
        max_threads = min(self.extraction_config.max_threads, 30)
        
        range_size = max_val - min_val
        number_threads = min(max_threads, max(1, range_size))
        increment = max(1, range_size // number_threads)
        
        self.logger.info(f"🔍 Generating {number_threads} partitioned queries - Range: {range_size}, Increment: {increment}")
        
        queries = []
        for i in range(number_threads):
            start_value = int(min_val + (increment * i))
            
            if i == number_threads - 1:
                end_value = max_val + 1  # Incluir el último valor
            else:
                end_value = int(min_val + (increment * (i + 1)))
            
            # Construir query particionada usando la configuración de tabla
            partitioned_query = self._build_partitioned_query(partition_column, start_value, end_value)
            
            queries.append({
                'query': partitioned_query,
                'thread_id': i,
                'metadata': {
                    **metadata,
                    'partition_index': i,
                    'start_range': start_value,
                    'end_range': end_value,
                    'chunking_params': self._get_chunking_params_for_partition()
                }
            })
        
        return queries

    def _parse_columns_for_partition(self) -> str:
        """Construye las columnas para queries particionadas"""
        columns_list = []
        
        # Agregar ID_COLUMN si existe
        if hasattr(self.table_config, 'id_column') and self.table_config.id_column and self.table_config.id_column.strip():
            id_column_expr = f"{self.table_config.id_column.strip()} as id"
            columns_list.append(id_column_expr)
        
        # Agregar las columnas regulares
        if self.table_config.columns and self.table_config.columns.strip():
            columns_list.append(self.table_config.columns.strip())
        else:
            columns_list.append('*')
        
        return ', '.join(columns_list)

    def _get_chunking_params_for_partition(self) -> dict:
        """Obtiene parámetros de chunking para particiones"""
        chunking_params = {}
        
        # Construir ORDER BY con PARTITION_COLUMN e ID_COLUMN
        order_by_parts = []
        
        # Si tiene partition_column configurado, agregarlo primero
        if hasattr(self.table_config, 'partition_column') and self.table_config.partition_column:
            order_by_parts.append(self.table_config.partition_column.strip())
        
        # Si tiene id_column configurado, agregarlo después
        if hasattr(self.table_config, 'id_column') and self.table_config.id_column and self.table_config.id_column.strip():
            order_by_parts.append(self.table_config.id_column.strip())
        
        # Si hay al menos una columna para order_by, agregarla
        if order_by_parts:
            chunking_params['order_by'] = ', '.join(order_by_parts)
        
        # Agregar chunk_size si está configurado
        if self.extraction_config.chunk_size:
            chunking_params['chunk_size'] = self.extraction_config.chunk_size
        
        return chunking_params

    def _build_partitioned_query(self, partition_column: str, start_value: int, end_value: int) -> str:
        """Construye una query particionada individual"""
        # Construir columnas con ID_COLUMN si existe
        columns = self._parse_columns_for_partition()
        
        # Construir FROM con JOINs
        from_clause = f"{self.table_config.source_schema}.{self.table_config.source_table}"
        if hasattr(self.table_config, 'join_expr') and self.table_config.join_expr:
            from_clause += f" {self.table_config.join_expr}"
        
        # Construir WHERE con partición y filtros
        where_conditions = [f"{partition_column} >= {start_value} AND {partition_column} < {end_value}"]
        
        if hasattr(self.table_config, 'filter_exp') and self.table_config.filter_exp:
            filter_exp = self.table_config.filter_exp.strip().replace('"', '')
            where_conditions.append(f"({filter_exp})")
        
        query = f"SELECT {columns} FROM {from_clause} WHERE {' AND '.join(where_conditions)}"
        
        self.logger.info(f"🔍 Query particionada generada - Rango: {start_value}-{end_value}")
        self.logger.info(f"📝 SQL Query particionada:\n{query}")
        return query

    def _execute_partitioned_queries(self, partitioned_queries: List[Dict[str, Any]]) -> tuple:
        """Ejecuta las queries particionadas en paralelo"""
        self.logger.info(
            f"🔍 Executing {len(partitioned_queries)} partitioned queries in parallel - "
            f"process_guid: {self.process_guid}"
        )
        
        files_created = []
        all_files_metadata = []  # 🆕
        total_records = 0
        
        max_workers = min(self.extraction_config.max_threads, len(partitioned_queries))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_query = {
                executor.submit(self._execute_partition_query, i, query): query
                for i, query in enumerate(partitioned_queries)
            }
            
            for future in as_completed(future_to_query):
                try:
                    # 🆕 Ahora recibe metadata también
                    partition_files, partition_metadata, record_count = future.result()
                    
                    if partition_files:
                        files_created.extend(partition_files)
                        all_files_metadata.extend(partition_metadata)
                        
                    total_records += record_count
                except Exception as e:
                    raise ExtractionError(f"Failed to execute partitioned query: {e}")
        
        return files_created, all_files_metadata, total_records

    def _handle_empty_result(self) -> tuple:
        """Handle case where no data was extracted"""
        files_created = []
        total_records = 0
        
        # Create empty file with schema if configured
        if self.table_config and self.table_config.columns:
            columns = [col.strip() for col in self.table_config.columns.split(',')]
            empty_df = pd.DataFrame(columns=columns)
            
            destination_path = self._build_destination_path()
            file_path = self.loader.load_dataframe(
                empty_df,
                destination_path,
                thread_id=0
            )
            files_created.append(file_path)
        
        return files_created, total_records
    
    def _build_destination_path(self) -> str:
        """Build destination path for files with configurable partition format"""
        # Obtener nombre limpio de tabla
        clean_table_name = self._get_clean_table_name()
        
        # 🆕 Generar ruta de partición usando el formato configurado
        partition_path = self.partition_formatter.format_path()
        
        return (f"{self.extraction_config.team}/"
                f"{self.extraction_config.data_source}/"
                f"{self.extraction_config.endpoint_name}/"
                f"{clean_table_name}/{partition_path}/")
    
    def _build_table_base_path(self) -> str:
        """
        Construye la ruta base de la tabla SIN particiones
        Se usa para limpieza completa en modo RESET
        """
        clean_table_name = self._get_clean_table_name()
        
        return (f"{self.extraction_config.team}/"
                f"{self.extraction_config.data_source}/"
                f"{self.extraction_config.endpoint_name}/"
                f"{clean_table_name}/")
    
    def _get_clean_table_name(self) -> str:
        """Extract clean table name from SOURCE_TABLE, removing alias after space"""
        if self.table_config and self.table_config.source_table:
            source_table = self.table_config.source_table
        else:
            source_table = self.extraction_config.table_name
        
        # Split by space and take only the first part (table name)
        clean_name = source_table.split()[0] if source_table and ' ' in source_table else source_table
        return clean_name
    
    def _build_metadata(self) -> Dict[str, Any]:
        """Build metadata for logging"""
        metadata = {
            'process_guid': self.process_guid,
            'project_name': self.extraction_config.project_name,
            'team': self.extraction_config.team,
            'data_source': self.extraction_config.data_source,
            'endpoint_name': self.extraction_config.endpoint_name,
            'environment': self.extraction_config.environment,
            'table_name': self.extraction_config.table_name
        }
        
        if self.database_config:
            metadata.update({
                'server': self.database_config.server,
                'username': self.database_config.username,
                'db_type': self.database_config.db_type
            })
        
        if self.strategy:
            metadata['strategy'] = self.strategy.get_strategy_name()
        
        return metadata
    
    def _execute_reset_cleanup(self) -> Dict[str, Any]:
        """
        Ejecuta el proceso de limpieza para modo RESET
        Reutiliza métodos de las clases existentes: S3Loader, DynamoDBWatermarkStorage, DynamoDBMonitor
        
        Returns:
            Dict consolidado con resultados del cleanup:
            {
                'success': bool,
                'total_items_deleted': int,
                'services_results': List[Dict],
                'errors': List[str]
            }
        """
        consolidated_result = {
            'success': True,
            'total_items_deleted': 0,
            'services_results': [],
            'errors': []
        }
        
        try:
            # 1. Limpiar datos en S3 Raw bucket
            if self.loader:
                try:
                    # 🔧 RESET: Usar ruta BASE sin particiones para limpiar TODO
                    table_base_path = self._build_table_base_path()
                    
                    s3_result = self.loader.cleanup_table_data(table_base_path)
                    s3_result['service_name'] = 'S3Loader'
                    consolidated_result['services_results'].append(s3_result)
                    
                    consolidated_result['total_items_deleted'] += s3_result.get('items_deleted', 0)
                    if not s3_result.get('success', False):
                        consolidated_result['success'] = False
                    if s3_result.get('errors'):
                        consolidated_result['errors'].extend(s3_result['errors'])
                    
                    # Solo loguear si hay items eliminados
                    items_deleted = s3_result.get('items_deleted', 0)
                    if items_deleted > 0:
                        self.logger.debug(f"S3 cleanup: {items_deleted} objetos eliminados")
                except Exception as e:
                    error_msg = f"Error en limpieza S3: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    consolidated_result['success'] = False
                    consolidated_result['errors'].append(error_msg)
                    consolidated_result['services_results'].append({
                        'service_name': 'S3Loader',
                        'success': False,
                        'items_deleted': 0,
                        'errors': [error_msg]
                    })
            
            # 2. Limpiar watermarks en DynamoDB
            if self.watermark_storage and hasattr(self.watermark_storage, 'cleanup_table_watermarks'):
                try:
                    watermark_result = self.watermark_storage.cleanup_table_watermarks(
                        self.extraction_config.table_name
                    )
                    watermark_result['service_name'] = 'DynamoDBWatermarkStorage'
                    consolidated_result['services_results'].append(watermark_result)
                    
                    consolidated_result['total_items_deleted'] += watermark_result.get('items_deleted', 0)
                    if not watermark_result.get('success', False):
                        consolidated_result['success'] = False
                    if watermark_result.get('errors'):
                        consolidated_result['errors'].extend(watermark_result['errors'])
                    
                    # Solo loguear si hay items eliminados
                    items_deleted = watermark_result.get('items_deleted', 0)
                    if items_deleted > 0:
                        self.logger.debug(f"Watermark cleanup: {items_deleted} items eliminados")
                except Exception as e:
                    error_msg = f"Error en limpieza de watermarks: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    consolidated_result['success'] = False
                    consolidated_result['errors'].append(error_msg)
                    consolidated_result['services_results'].append({
                        'service_name': 'DynamoDBWatermarkStorage',
                        'success': False,
                        'items_deleted': 0,
                        'errors': [error_msg]
                    })
            
            # 3. Limpiar logs en DynamoDB
            if self.monitor and hasattr(self.monitor, 'cleanup_table_logs'):
                try:
                    logs_result = self.monitor.cleanup_table_logs(self.extraction_config.table_name)
                    logs_result['service_name'] = 'DynamoDBMonitor'
                    consolidated_result['services_results'].append(logs_result)
                    
                    consolidated_result['total_items_deleted'] += logs_result.get('items_deleted', 0)
                    if not logs_result.get('success', False):
                        consolidated_result['success'] = False
                    if logs_result.get('errors'):
                        consolidated_result['errors'].extend(logs_result['errors'])
                    
                    # Solo loguear si hay items eliminados
                    items_deleted = logs_result.get('items_deleted', 0)
                    if items_deleted > 0:
                        self.logger.debug(f"Logs cleanup: {items_deleted} items eliminados")
                except Exception as e:
                    error_msg = f"Error en limpieza de logs: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    consolidated_result['success'] = False
                    consolidated_result['errors'].append(error_msg)
                    consolidated_result['services_results'].append({
                        'service_name': 'DynamoDBMonitor',
                        'success': False,
                        'items_deleted': 0,
                        'errors': [error_msg]
                    })
            
            # Log resumen final - solo si hay items eliminados o errores
            total_deleted = consolidated_result['total_items_deleted']
            if consolidated_result['success']:
                if total_deleted > 0:
                    self.logger.info(f"✅ Limpieza RESET completada - {total_deleted} items eliminados")
            else:
                self.logger.warning(
                    f"⚠️ Limpieza RESET con errores - "
                    f"Items eliminados: {total_deleted}, "
                    f"Errores: {len(consolidated_result['errors'])}"
                )
            
            return consolidated_result
            
        except Exception as e:
            error_msg = f"Error ejecutando reset cleanup: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'total_items_deleted': 0,
                'services_results': [],
                'errors': [error_msg],
                'details': error_msg
            }
    
    def _cleanup(self):
        """Cleanup resources"""
        if self.extractor:
            try:
                self.extractor.close()
            except Exception:
                pass
     
    def _execute_partition_query(self, thread_id: int, query_metadata: Dict[str, Any]) -> tuple:
        """Ejecuta una query particionada individual con metadata completa"""
        query = query_metadata['query']
        metadata = query_metadata.get('metadata', {})
        
        partition_index = metadata.get('partition_index', 'N/A')
        self.logger.info(
            f"🔍 Thread {thread_id} - Ejecutando query particionada (Partition {partition_index})"
        )
        
        # Mostrar query ANTES de ejecutarse para validación
        self.logger.info(f"📝 SQL Query (Thread {thread_id}, Partition {partition_index}):\n{query}")
        
        files_created = []
        files_metadata = []
        total_records = 0
        
        try:
            chunk_size = metadata.get('chunk_size', self.extraction_config.chunk_size)
            chunking_params = metadata.get('chunking_params', {})
            order_by = chunking_params.get('order_by')
            
            destination_path = metadata.get('destination_path', self._build_destination_path())
            
            chunk_count = 0
            for chunk_df in self.extractor.extract_data(query, chunk_size, order_by):
                chunk_count += 1
                
                if chunk_df is not None and not chunk_df.empty:
                    self.logger.info(f"🔍 DEBUG: Processing chunk {chunk_count} with {len(chunk_df)} rows")
                    
                    # Cargar chunk
                    file_path = self.loader.load_dataframe(
                        chunk_df, 
                        destination_path, 
                        thread_id=f"{thread_id}_{chunk_count-1}",
                        chunk_id=chunk_count-1
                    )
                    
                    if file_path:
                        files_created.append(file_path)
                        
                        # 🆕 Obtener tamaño del archivo desde S3
                        file_size_bytes = self._get_s3_file_size(file_path)
                        file_size_mb = round(file_size_bytes / (1024 * 1024), 2) if file_size_bytes else 0
                        
                        # Construir metadata completa
                        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                        file_metadata = {
                            'file_path': file_path,
                            'file_name': file_name,
                            'file_size_bytes': file_size_bytes,
                            'file_size_mb': file_size_mb,
                            'records_count': len(chunk_df),
                            'columns_count': len(chunk_df.columns),
                            'thread_id': str(thread_id),
                            'chunk_id': chunk_count - 1,
                            'partition_index': partition_index,
                            'created_at': datetime.now().isoformat(),
                            'compression': 'snappy',  # Por defecto en parquet
                            'format': 'parquet'
                        }
                        files_metadata.append(file_metadata)
                    
                    total_records += len(chunk_df)
                    
                    self.logger.info(
                        f"📁 File created: {file_name} | "
                        f"Size: {file_size_mb}MB | "
                        f"Records: {len(chunk_df):,} | "
                        f"Columns: {len(chunk_df.columns)}"
                    )
            
            self.logger.info(
                f"✅ Thread {thread_id} completed: {total_records:,} records, "
                f"{len(files_created)} files, "
                f"{sum(f['file_size_mb'] for f in files_metadata):.2f}MB total"
            )
            
            return files_created, files_metadata, total_records
            
        except Exception as e:
            self.logger.error(f"❌ ERROR in _execute_partition_query for thread {thread_id}: {e}")
            import traceback
            self.logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            raise ExtractionError(f"Failed to execute partition query for thread {thread_id}: {e}")

    def _get_s3_file_size(self, s3_path: str) -> int:
        """Obtiene el tamaño de un archivo en S3"""
        try:
            # Remover prefijo s3://
            if s3_path.startswith('s3://'):
                s3_path = s3_path[5:]
            
            # Separar bucket y key
            parts = s3_path.split('/', 1)
            if len(parts) != 2:
                return 0
                
            bucket_name, key = parts
            
            # Obtener metadata del archivo
            import boto3
            s3_client = boto3.client('s3')
            response = s3_client.head_object(Bucket=bucket_name, Key=key)
            
            return response['ContentLength']
            
        except Exception as e:
            self.logger.warning(f"No se pudo obtener tamaño de archivo {s3_path}: {e}")
            return 0