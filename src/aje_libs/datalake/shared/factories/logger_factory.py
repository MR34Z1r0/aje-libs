"""
Factory para crear servicios de logging (OCP)
"""
from typing import Optional, Dict, Type
from ..contracts.logging import ILogger
from ..services.logging import LoggerService
from ..exceptions import ConfigurationException


class LoggerFactory:
    """Factory para crear servicios de logging (OCP - extensible sin modificar)"""
    
    _logger_types: Dict[str, Type[ILogger]] = {
        'default': LoggerService,
        'datalake': LoggerService,
    }
    
    @classmethod
    def create(cls, logger_type: str = 'default', logger_name: Optional[str] = None, **config) -> ILogger:
        """
        Crea servicio de logging
        
        Args:
            logger_type: Tipo de logger ('default', 'datalake')
            logger_name: Nombre del logger
            **config: Configuración adicional
            
        Returns:
            Instancia de ILogger
        """
        logger_type_lower = logger_type.lower()
        
        if logger_type_lower not in cls._logger_types:
            available = ', '.join(cls._logger_types.keys())
            raise ConfigurationException(
                f"Tipo de logger no soportado '{logger_type}'. Disponibles: {available}"
            )
        
        logger_class = cls._logger_types[logger_type_lower]
        
        # Configurar globalmente si se proporciona configuración
        if config:
            LoggerService.configure_global(**config)
        
        return logger_class(logger_name)
    
    @classmethod
    def register_logger(cls, logger_type: str, logger_class: Type[ILogger]):
        """Registra un nuevo tipo de logger (OCP - extensible)"""
        cls._logger_types[logger_type.lower()] = logger_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de logger soportados"""
        return list(cls._logger_types.keys())

