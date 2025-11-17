"""
Módulo de soporte para Apache Iceberg.
Proporciona implementación de IDataWriter y utilidades para tablas Apache Iceberg.
"""
from .iceberg_table_writer import IcebergTableWriter
from .iceberg_table_manager import TimeRangeDeleteManager

__all__ = [
    'IcebergTableWriter',
    'TimeRangeDeleteManager',
]

