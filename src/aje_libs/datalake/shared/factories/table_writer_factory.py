# -*- coding: utf-8 -*-
"""
Factory para crear Table Writers (Delta, Iceberg, etc.) - OCP - extensible sin modificar
Aplica Factory Pattern y Registry Pattern para soportar múltiples formatos de tablas
"""
from typing import Dict, Type, Optional
from ..contracts.storage import IDataWriter
from ..contracts.logging import ILogger
from ..services.logging import LoggerService
from ..exceptions import ConfigurationException


class TableWriterFactory:
    """
    Factory para crear instancias de IDataWriter según el formato de tabla especificado.
    Aplica OCP (Open/Closed Principle) - extensible sin modificar el código existente.
    """
    
    _writer_types: Dict[str, Type[IDataWriter]] = {}
    
    @classmethod
    def register_writer(cls, writer_type: str, writer_class: Type[IDataWriter]):
        """
        Registra un nuevo tipo de writer (OCP - permite extensión sin modificar el factory)
        
        Args:
            writer_type: Tipo de writer ('delta', 'iceberg', etc.)
            writer_class: Clase que implementa IDataWriter
            
        Raises:
            TypeError: Si la clase no implementa IDataWriter
            ValueError: Si el tipo ya está registrado
        """
        if not issubclass(writer_class, IDataWriter):
            raise TypeError(
                f"La clase '{writer_class.__name__}' debe implementar IDataWriter"
            )
        
        writer_type_lower = writer_type.lower()
        
        if writer_type_lower in cls._writer_types:
            logger = LoggerService.get_logger(__name__)
            logger.warning(
                f"El writer type '{writer_type}' ya está registrado. Sobrescribiendo con '{writer_class.__name__}'"
            )
        
        cls._writer_types[writer_type_lower] = writer_class
        
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"✅ Writer registrado: {writer_type} -> {writer_class.__name__}")
    
    @classmethod
    def create(
        cls,
        writer_type: str,
        spark,
        logger: Optional[ILogger] = None,
        **kwargs
    ) -> IDataWriter:
        """
        Crea una instancia de IDataWriter según el tipo especificado
        
        Args:
            writer_type: Tipo de writer ('delta', 'iceberg', etc.)
            spark: SparkSession
            logger: Logger (opcional)
            **kwargs: Argumentos adicionales específicos del writer
            
        Returns:
            Instancia de IDataWriter configurada
            
        Raises:
            ConfigurationException: Si el tipo de writer no está registrado
        """
        writer_type_lower = writer_type.lower()
        
        if writer_type_lower not in cls._writer_types:
            available = ', '.join(cls._writer_types.keys())
            raise ConfigurationException(
                f"Tipo de writer no soportado '{writer_type}'. "
                f"Disponibles: {available}. "
                f"Usa TableWriterFactory.register_writer() para registrar nuevos tipos."
            )
        
        writer_class = cls._writer_types[writer_type_lower]
        
        # Crear instancia con los parámetros proporcionados
        try:
            return writer_class(spark=spark, logger=logger, **kwargs)
        except Exception as e:
            logger_instance = logger or LoggerService.get_logger(__name__)
            logger_instance.error(f"Error creando writer '{writer_type}': {e}")
            raise ConfigurationException(f"Error creando writer '{writer_type}': {e}") from e
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Retorna lista de tipos de writers soportados"""
        return list(cls._writer_types.keys())
    
    @classmethod
    def is_supported(cls, writer_type: str) -> bool:
        """Verifica si un tipo de writer está soportado"""
        return writer_type.lower() in cls._writer_types


# Auto-registrar writers disponibles
def register_default_writers():
    """
    Registra los writers por defecto (Delta Lake, Iceberg, Parquet/PySpark puro).
    Esta función se llama automáticamente, pero también se puede llamar manualmente
    si se necesita registrar writers personalizados.
    """
    try:
        from ...light_transform.services.storage.delta.delta_table_writer import DeltaTableWriter
        TableWriterFactory.register_writer('delta', DeltaTableWriter)
        logger = LoggerService.get_logger(__name__)
        logger.debug("✅ DeltaTableWriter registrado")
    except ImportError as e:
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"No se pudo registrar DeltaTableWriter (puede ser esperado si no está disponible): {e}")
    
    try:
        from ...light_transform.services.storage.iceberg.iceberg_table_writer import IcebergTableWriter
        TableWriterFactory.register_writer('iceberg', IcebergTableWriter)
        logger = LoggerService.get_logger(__name__)
        logger.debug("✅ IcebergTableWriter registrado")
    except ImportError as e:
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"No se pudo registrar IcebergTableWriter (puede ser esperado si no está disponible): {e}")
    
    try:
        from ...light_transform.services.storage.parquet.parquet_table_writer import ParquetTableWriter
        TableWriterFactory.register_writer('parquet', ParquetTableWriter)
        TableWriterFactory.register_writer('spark', ParquetTableWriter)  # Alias para 'spark'
        logger = LoggerService.get_logger(__name__)
        logger.debug("✅ ParquetTableWriter registrado (PySpark puro)")
    except ImportError as e:
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"No se pudo registrar ParquetTableWriter (puede ser esperado si no está disponible): {e}")


# Registrar automáticamente al importar
register_default_writers()

