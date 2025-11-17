"""
Configuración centralizada para aje_libs/datalake
✅ Evita valores hardcodeados en el código
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class ExtractionSettings:
    """Configuración para extracción de datos"""
    
    # Tamaños de chunks
    default_chunk_size: int = 10000
    max_chunk_size: int = 100000
    min_chunk_size: int = 1000
    
    # Timeouts (segundos)
    default_query_timeout: int = 300  # 5 minutos
    max_query_timeout: int = 3600     # 1 hora
    connection_timeout: int = 30
    
    # Retry
    default_max_retries: int = 3
    default_retry_delay: float = 1.0  # segundos
    max_retry_delay: float = 60.0
    
    # Watermarks
    watermark_retention_days: int = 90
    max_watermark_history: int = 100
    
    # S3
    s3_upload_chunk_size: int = 8388608  # 8 MB
    s3_max_concurrent_uploads: int = 10
    
    # Cleanup
    cleanup_batch_size: int = 1000  # Para eliminar objetos de S3/DynamoDB en lotes
    
    # Logging
    log_rotation_max_bytes: int = 10485760  # 10 MB
    log_rotation_backup_count: int = 5
    
    # Particiones
    default_partition_format: str = "year={year}/month={month}/day={day}"
    
    # Validación
    max_column_name_length: int = 255
    max_table_name_length: int = 255
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'ExtractionSettings':
        """Crea settings desde un diccionario"""
        return cls(**{k: v for k, v in config.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LightTransformSettings:
    """Configuración para light transform"""
    
    # Spark
    spark_default_parallelism: int = 200
    spark_max_result_size: str = "2g"
    spark_dynamic_allocation: bool = True
    
    # Delta/Iceberg
    delta_auto_optimize: bool = True
    delta_auto_compact: bool = False
    iceberg_table_properties: Dict[str, str] = field(default_factory=dict)
    
    # Write operations
    merge_batch_size: int = 10000
    overwrite_mode: str = "dynamic"  # "static" o "dynamic"
    
    # Validación de datos
    data_quality_checks: bool = True
    strict_schema_validation: bool = False
    
    # Performance
    coalesce_partitions: bool = True
    repartition_threshold: int = 1000
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'LightTransformSettings':
        """Crea settings desde un diccionario"""
        return cls(**{k: v for k, v in config.items() if k in cls.__dataclass_fields__})


# Singleton global para settings (puede ser sobrescrito)
_extraction_settings: Optional[ExtractionSettings] = None
_light_transform_settings: Optional[LightTransformSettings] = None


def get_settings() -> ExtractionSettings:
    """Obtiene configuración de extracción (singleton)"""
    global _extraction_settings
    if _extraction_settings is None:
        _extraction_settings = ExtractionSettings()
    return _extraction_settings


def get_light_transform_settings() -> LightTransformSettings:
    """Obtiene configuración de light transform (singleton)"""
    global _light_transform_settings
    if _light_transform_settings is None:
        _light_transform_settings = LightTransformSettings()
    return _light_transform_settings


def configure_extraction_settings(settings: ExtractionSettings) -> None:
    """Configura settings de extracción (útil para tests o personalización)"""
    global _extraction_settings
    _extraction_settings = settings


def configure_light_transform_settings(settings: LightTransformSettings) -> None:
    """Configura settings de light transform (útil para tests o personalización)"""
    global _light_transform_settings
    _light_transform_settings = settings

