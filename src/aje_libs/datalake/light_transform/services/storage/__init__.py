"""
Servicios de almacenamiento para light_transform.
Proporciona soporte para múltiples formatos de tablas (Delta Lake, Apache Iceberg, etc.)
con estructura estándar y modular.
"""

# ✅ Registrar writers automáticamente al importar
from . import table_writers_registry  # noqa: F401

# ✅ Importar desde módulos organizados por formato
from .delta import DeltaTableWriter, TimeRangeDeleteManager as DeltaTimeRangeDeleteManager
from .iceberg import IcebergTableWriter, TimeRangeDeleteManager as IcebergTimeRangeDeleteManager
from .parquet import ParquetTableWriter

__all__ = [
    # Delta Lake
    'DeltaTableWriter',
    'DeltaTimeRangeDeleteManager',
    # Apache Iceberg
    'IcebergTableWriter',
    'IcebergTimeRangeDeleteManager',
    # PySpark puro (Parquet)
    'ParquetTableWriter',
]

