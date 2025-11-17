# -*- coding: utf-8 -*-
"""
Builder para configuraciones de Spark según el formato de tabla (Delta, Iceberg, etc.)
Aplica Strategy Pattern y Builder Pattern (OCP, SRP)
"""
from typing import Dict, Optional, Any, TYPE_CHECKING

# Importar pyspark de forma diferida para evitar requerirlo en extract_data
try:
    from pyspark.sql import SparkSession
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False
    SparkSession = None  # type: ignore

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

from ..contracts.logging import ILogger
from ..services.logging import LoggerService


class SparkConfigBuilder:
    """
    Builder para configurar SparkSession según el formato de tabla seleccionado.
    Aplica OCP (Open/Closed) - extensible para nuevos formatos sin modificar código existente.
    """
    
    _format_configs: Dict[str, Dict[str, str]] = {
        'delta': {
            'extensions': 'io.delta.sql.DeltaSparkSessionExtension',
            'catalog': 'org.apache.spark.sql.delta.catalog.DeltaCatalog',
            'retention_duration_check': 'spark.databricks.delta.retentionDurationCheck.enabled',
            'schema_auto_merge': 'spark.databricks.delta.schema.autoMerge.enabled',
        },
        'iceberg': {
            'extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            'catalog': 'org.apache.iceberg.spark.SparkSessionCatalog',
            'catalog_impl': 'org.apache.iceberg.aws.glue.GlueCatalog',  # Para AWS Glue Catalog
            'warehouse': 'spark.sql.catalog.spark_catalog.warehouse',
        },
    }
    
    @classmethod
    def configure_for_format(
        cls,
        spark_builder: Any,  # SparkSession.Builder cuando pyspark está disponible
        table_format: str = 'delta',
        logger: Optional[ILogger] = None,
        **additional_configs
    ) -> Any:  # SparkSession.Builder cuando pyspark está disponible
        """
        Configura el SparkSession.Builder para el formato de tabla especificado
        
        Args:
            spark_builder: SparkSession.Builder a configurar
            table_format: Formato de tabla ('delta', 'iceberg')
            logger: Logger (opcional)
            **additional_configs: Configuraciones adicionales específicas del formato
            
        Returns:
            SparkSession.Builder configurado
            
        Raises:
            ImportError: Si pyspark no está disponible
            ValueError: Si el formato no es soportado
        """
        # Usar la variable global de disponibilidad de pyspark
        global PYSPARK_AVAILABLE
        if not PYSPARK_AVAILABLE:
            # Intentar importar pyspark en tiempo de ejecución una sola vez
            try:
                from pyspark.sql import SparkSession  # noqa: F401
                PYSPARK_AVAILABLE = True
            except ImportError as exc:  # pragma: no cover - rama dependiente de entorno
                raise ImportError(
                    "pyspark no está disponible. "
                    "SparkConfigBuilder requiere pyspark para funcionar. "
                    "Instala con: pip install pyspark"
                ) from exc
        
        logger_instance = logger or LoggerService.get_logger(__name__)
        table_format_lower = table_format.lower()
        
        if table_format_lower not in cls._format_configs:
            available = ', '.join(cls._format_configs.keys())
            raise ValueError(
                f"Formato de tabla no soportado '{table_format}'. Disponibles: {available}"
            )
        
        config = cls._format_configs[table_format_lower]
        
        # Configuraciones base comunes
        spark_builder.config("spark.sql.adaptive.enabled", "true")
        spark_builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        spark_builder.config("spark.sql.adaptive.skewJoin.enabled", "true")
        spark_builder.config("spark.sql.adaptive.localShuffleReader.enabled", "true")
        spark_builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        spark_builder.config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        
        # Configuraciones específicas del formato
        if table_format_lower == 'delta':
            spark_builder.config("spark.sql.extensions", config['extensions'])
            spark_builder.config("spark.sql.catalog.spark_catalog", config['catalog'])
            spark_builder.config(config['retention_duration_check'], "false")
            spark_builder.config(config['schema_auto_merge'], "true")
            
        elif table_format_lower == 'iceberg':
            spark_builder.config("spark.sql.extensions", config['extensions'])
            spark_builder.config("spark.sql.catalog.spark_catalog", config['catalog'])
            spark_builder.config(f"spark.sql.catalog.spark_catalog.catalog-impl", config['catalog_impl'])
            
            # Configurar warehouse si se proporciona
            if 'warehouse_path' in additional_configs:
                spark_builder.config(config['warehouse'], additional_configs['warehouse_path'])
        
        # Aplicar configuraciones adicionales
        for key, value in additional_configs.items():
            if not key.startswith('spark.'):
                key = f"spark.{key}"
            spark_builder.config(key, str(value))
        
        logger_instance.debug(f"✅ Spark configurado para formato: {table_format}")
        
        return spark_builder
    
    @classmethod
    def get_format_config(cls, table_format: str) -> Dict[str, str]:
        """Obtiene la configuración para un formato específico"""
        table_format_lower = table_format.lower()
        if table_format_lower not in cls._format_configs:
            raise ValueError(f"Formato no soportado: {table_format}")
        return cls._format_configs[table_format_lower].copy()
    
    @classmethod
    def register_format_config(cls, table_format: str, config: Dict[str, str]):
        """
        Registra una nueva configuración de formato (OCP - extensible)
        
        Args:
            table_format: Nombre del formato ('delta', 'iceberg', etc.)
            config: Diccionario con las configuraciones necesarias
        """
        cls._format_configs[table_format.lower()] = config.copy()
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"✅ Configuración de formato registrada: {table_format}")


__all__ = ['SparkConfigBuilder']

