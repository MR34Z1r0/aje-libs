"""
Módulo de soporte para PySpark puro (Parquet).
Proporciona implementación de IDataWriter usando solo PySpark sin Delta Lake ni Iceberg.
"""
from .parquet_table_writer import ParquetTableWriter

__all__ = [
    'ParquetTableWriter',
]

