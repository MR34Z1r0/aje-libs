# strategies/adapters/strategy_adapter.py
from typing import List, Dict, Any, Optional
from ...contracts.strategy_interface import IExtractionStrategy
from ...contracts.query_builder_interface import IQueryBuilder
from ..base.extraction_strategy import ExtractionStrategy
from ....shared.models import ExtractionParams  # ✅ ExtractionParams desde shared/models
from ....shared.services.logging import LoggerService
from ....shared.utils.partition_formatter import PartitionFormatter
from ...factories.query_builder_factory import QueryBuilderFactory

logger = LoggerService.get_logger(__name__)

class StrategyAdapter(IExtractionStrategy):
    """Adaptador para hacer compatible la nueva estrategia con la interfaz existente"""
    
    def __init__(self, new_strategy: ExtractionStrategy, table_config: Optional[Any] = None, db_type: Optional[str] = None):
        self.new_strategy = new_strategy
        self.extraction_params = None
        self.watermark_storage = new_strategy.watermark_storage
        # 🆕 Inicializar formateador de particiones
        self.table_config = table_config or getattr(new_strategy, 'table_config', None)
        partition_format = None
        if self.table_config and hasattr(self.table_config, 'partition_format'):
            partition_format = self.table_config.partition_format
        self.partition_formatter = PartitionFormatter(partition_format)
        
        # 🆕 Inicializar Query Builder específico por base de datos
        self.query_builder: Optional[IQueryBuilder] = None
        if db_type and self.table_config:
            try:
                self.query_builder = QueryBuilderFactory.create(
                    db_type=db_type,
                    table_config=self.table_config
                )
                logger.debug(f"✅ QueryBuilder inicializado: {type(self.query_builder).__name__} para DB: {db_type}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo crear QueryBuilder para {db_type}: {e}. Usando construcción de query genérica.")
        else:
            logger.debug("⚠️ QueryBuilder no inicializado - db_type o table_config no disponible")
        
        # Log del formato que se usará
        logger.debug(f"StrategyAdapter inicializado - Formato de partición: {self.partition_formatter.format_template}")

    def generate_queries(self) -> List[Dict[str, Any]]:
        """Adapta el nuevo método build_extraction_params al formato esperado"""
        logger.debug("Strategy Adapter - Generating queries")
        
        # Obtener parámetros de extracción
        self.extraction_params = self.new_strategy.build_extraction_params()
        
        # Verificar si necesita particionado
        if self.extraction_params.metadata.get('needs_partitioning', False):
            logger.info("Partitioned load detected - returning min/max query")
            return self._generate_min_max_query()
        
        # Para cargas estándar
        query = self._build_query_from_params(self.extraction_params)
        
        query_dict = {
            'query': query,
            'thread_id': 0,
            'metadata': {
                'strategy': self.new_strategy.strategy_name,
                'table_name': self.new_strategy.extraction_config.table_name,
                'destination_path': self._build_destination_path(),
                'chunking_params': self._get_chunking_params(),
                'partition_format': self.partition_formatter.format_template,
                **self.extraction_params.metadata
            }
        }
        
        return [query_dict]
    
    def _generate_min_max_query(self) -> List[Dict[str, Any]]:
        """Genera query de min/max para particionado"""
        partition_column = self.extraction_params.metadata['partition_column']
        
        # 🆕 Usar QueryBuilder si está disponible, sino usar construcción genérica
        if self.query_builder:
            existing_where = self.extraction_params.get_where_clause()
            min_max_query = self.query_builder.build_min_max_query(
                column=partition_column,
                additional_where=existing_where
            )
        else:
            # Fallback a construcción genérica
            table_name_with_joins = self.extraction_params.table_name
            min_max_query = f"SELECT MIN({partition_column}) as min_val, MAX({partition_column}) as max_val FROM {table_name_with_joins}"
            
            where_conditions = [f"{partition_column} <> 0"]
            existing_where = self.extraction_params.get_where_clause()
            if existing_where:
                where_conditions.append(existing_where)
            
            if where_conditions:
                min_max_query += f" WHERE {' AND '.join(where_conditions)}"
        
        logger.info("🔍 Query MIN/MAX generada")
        logger.info(f"📝 SQL Query MIN/MAX:\n{min_max_query}")
        
        return [{
            'query': min_max_query,
            'thread_id': 0,
            'metadata': {
                'strategy': self.new_strategy.strategy_name,
                'table_name': self.new_strategy.extraction_config.table_name,
                'query_type': 'min_max',
                'partition_column': partition_column,
                'needs_partitioned_queries': True,
                'partition_format': self.partition_formatter.format_template,
                **self.extraction_params.metadata
            }
        }]

    def get_strategy_name(self) -> str:
        """Delega al nombre de la nueva estrategia"""
        return self.new_strategy.strategy_name
    
    def validate_config(self) -> bool:
        """Delega a la validación de la nueva estrategia"""
        return self.new_strategy.validate_and_cache()
    
    def estimate_resources(self) -> Dict[str, Any]:
        """Delega a la estimación de recursos de la nueva estrategia"""
        return self.new_strategy.estimate_resources()
    
    def _build_query_from_params(self, params: ExtractionParams) -> str:
        """
        Construye la query SQL a partir de los parámetros de extracción.
        
        🆕 Usa QueryBuilder específico por base de datos si está disponible,
        sino usa construcción genérica como fallback.
        """
        # 🆕 Usar QueryBuilder si está disponible
        if self.query_builder:
            return self.query_builder.build_select_query(params)
        
        # Fallback a construcción genérica (compatible con cualquier DB)
        columns_str = ', '.join(params.columns) if params.columns != ['*'] else '*'
        table_name = params.table_name
        where_clause = params.get_where_clause()
        
        query = f"SELECT {columns_str} FROM {table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if params.order_by:
            query += f" ORDER BY {params.order_by}"
        
        if params.limit:
            # ⚠️ LIMIT es genérico, pero algunos DBs usan TOP (SQL Server)
            # En el fallback usamos LIMIT que funciona en PostgreSQL, MySQL, etc.
            query += f" LIMIT {params.limit}"
        
        return query
    
    def _build_destination_path(self) -> str:
        """Construye el path de destino S3 con formato configurable"""
        # Obtener nombre de tabla limpio
        clean_table_name = self._get_clean_table_name()
        
        # 🆕 Generar ruta de partición usando el formato configurado
        partition_path = self.partition_formatter.format_path()
        
        # Log para debugging
        logger.debug(f"Building destination path with partition format: {self.partition_formatter.format_template}")
        logger.debug(f"Generated partition path: {partition_path}")
        
        destination_path = (f"{self.new_strategy.extraction_config.team}/"
                          f"{self.new_strategy.extraction_config.data_source}/"
                          f"{self.new_strategy.extraction_config.endpoint_name}/"
                          f"{clean_table_name}/{partition_path}/")
        
        logger.info(f"📁 Final destination path: {destination_path}")
        
        return destination_path
    
    def _get_clean_table_name(self) -> str:
        """Extrae nombre de tabla limpio"""
        source_table = (self.new_strategy.table_config.source_table or 
                       self.new_strategy.extraction_config.table_name)
        
        if source_table and ' ' in source_table:
            return source_table.split()[0]
        return source_table
    
    def _get_chunking_params(self) -> Dict[str, Any]:
        """Obtiene parámetros de chunking"""
        if not self.extraction_params:
            return {}
        
        chunking_params = {}
        
        if self.extraction_params.chunk_size:
            chunking_params['chunk_size'] = self.extraction_params.chunk_size
        
        if self.extraction_params.chunk_column:
            chunking_params['order_by'] = self.extraction_params.chunk_column
        
        return chunking_params