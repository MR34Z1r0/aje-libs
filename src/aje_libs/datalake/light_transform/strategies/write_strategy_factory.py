# -*- coding: utf-8 -*-
"""
Factory para crear estrategias de escritura según load_type (OCP - Open/Closed Principle)
Mapea load_type a la estrategia de escritura apropiada

Uso:
    # Automático (usado por DataProcessor)
    strategy = WriteStrategyFactory.create('incremental')
    
    # Registrar estrategia personalizada
    WriteStrategyFactory.register_strategy('custom', CustomStrategy)

Mapeo de load_type a estrategias:
    - 'full' → FullLoadStrategy (OVERWRITE)
    - 'incremental' → IncrementalStrategy (MERGE/APPEND)
    - 'time_range' o 'between-date' → TimeRangeStrategy (DELETE+INSERT)
"""
from typing import Dict, Type, Optional

from ..contracts.storage.write_strategy_interface import IWriteStrategy
from .write_strategies import (
    FullLoadStrategy,
    IncrementalStrategy,
    TimeRangeStrategy,
)
from ...shared.services.logging import LoggerService
from ...shared.exceptions import ConfigurationException


class WriteStrategyFactory:
    """
    Factory para crear estrategias de escritura según el load_type de la tabla.
    Aplica OCP (Open/Closed Principle) - extensible sin modificar código existente.
    """
    
    _strategy_map: Dict[str, Type[IWriteStrategy]] = {
        'full': FullLoadStrategy,
        'incremental': IncrementalStrategy,
        'time_range': TimeRangeStrategy,
        'between-date': TimeRangeStrategy,  # Alias para time_range
    }
    
    @classmethod
    def create(cls, load_type: str) -> IWriteStrategy:
        """
        Crea una estrategia de escritura según el load_type
        
        Args:
            load_type: Tipo de carga ('full', 'incremental', 'time_range', 'between-date')
            
        Returns:
            Instancia de IWriteStrategy
            
        Raises:
            ConfigurationException: Si el load_type no es soportado
        """
        load_type_lower = load_type.lower().strip()
        
        if load_type_lower not in cls._strategy_map:
            available = ', '.join(cls._strategy_map.keys())
            raise ConfigurationException(
                f"Load type no soportado '{load_type}'. "
                f"Disponibles: {available}. "
                f"Usa WriteStrategyFactory.register_strategy() para registrar nuevos tipos."
            )
        
        strategy_class = cls._strategy_map[load_type_lower]
        return strategy_class()
    
    @classmethod
    def register_strategy(cls, load_type: str, strategy_class: Type[IWriteStrategy]):
        """
        Registra una nueva estrategia de escritura (OCP - extensible)
        
        Args:
            load_type: Tipo de carga a registrar
            strategy_class: Clase que implementa IWriteStrategy
            
        Raises:
            TypeError: Si la clase no implementa IWriteStrategy
        """
        if not issubclass(strategy_class, IWriteStrategy):
            raise TypeError(
                f"La clase '{strategy_class.__name__}' debe implementar IWriteStrategy"
            )
        
        load_type_lower = load_type.lower()
        cls._strategy_map[load_type_lower] = strategy_class
        
        logger = LoggerService.get_logger(__name__)
        logger.debug(f"✅ Estrategia de escritura registrada: {load_type} -> {strategy_class.__name__}")
    
    @classmethod
    def get_supported_load_types(cls) -> list:
        """Retorna lista de load_types soportados"""
        return list(cls._strategy_map.keys())
    
    @classmethod
    def is_supported(cls, load_type: str) -> bool:
        """Verifica si un load_type está soportado"""
        return load_type.lower().strip() in cls._strategy_map


__all__ = ['WriteStrategyFactory']

