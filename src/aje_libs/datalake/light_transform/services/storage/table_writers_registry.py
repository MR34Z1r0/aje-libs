# -*- coding: utf-8 -*-
"""
Registry para registrar table writers automáticamente al importar
Asegura que Delta e Iceberg estén disponibles sin configuración adicional
"""
from aje_libs.datalake.shared.factories import TableWriterFactory
from aje_libs.datalake.shared.services.logging import LoggerService

logger = LoggerService.get_logger(__name__)


def register_table_writers():
    """
    Registra todos los table writers disponibles (Delta, Iceberg, Parquet/PySpark puro)
    Esto permite usar TableWriterFactory sin configuración manual
    """
    try:
        # Registrar DeltaTableWriter
        from .delta.delta_table_writer import DeltaTableWriter
        TableWriterFactory.register_writer('delta', DeltaTableWriter)
        logger.debug("✅ DeltaTableWriter registrado")
    except ImportError as e:
        logger.warning(f"⚠️ No se pudo registrar DeltaTableWriter: {e}")
    
    try:
        # Registrar IcebergTableWriter
        from .iceberg.iceberg_table_writer import IcebergTableWriter
        TableWriterFactory.register_writer('iceberg', IcebergTableWriter)
        logger.debug("✅ IcebergTableWriter registrado")
    except ImportError as e:
        logger.warning(f"⚠️ No se pudo registrar IcebergTableWriter: {e}")
    
    try:
        # Registrar ParquetTableWriter (PySpark puro, sin Delta/Iceberg)
        from .parquet.parquet_table_writer import ParquetTableWriter
        TableWriterFactory.register_writer('parquet', ParquetTableWriter)
        TableWriterFactory.register_writer('spark', ParquetTableWriter)  # Alias para 'spark'
        logger.debug("✅ ParquetTableWriter registrado (PySpark puro)")
    except ImportError as e:
        logger.warning(f"⚠️ No se pudo registrar ParquetTableWriter: {e}")


# Registrar automáticamente al importar este módulo
register_table_writers()

