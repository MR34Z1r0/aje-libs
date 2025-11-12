# strategies/registry/strategy_registry.py
from typing import Dict, Type
from ..base.extraction_strategy import ExtractionStrategy
from ..base.strategy_types import ExtractionStrategyType
from ....shared.services.logging import LoggerService

logger = LoggerService.get_logger(__name__)

class StrategyRegistry:
    """Registro central de estrategias de extracción"""
    
    _strategies: Dict[ExtractionStrategyType, Type[ExtractionStrategy]] = {}
    
    @classmethod
    def register(cls, strategy_type: ExtractionStrategyType, strategy_class: Type[ExtractionStrategy]):
        """Registra una nueva estrategia"""
        # No loguear cada registro individual, se resumirá al final
        cls._strategies[strategy_type] = strategy_class
    
    @classmethod
    def get_strategy_class(cls, strategy_type: ExtractionStrategyType) -> Type[ExtractionStrategy]:
        """Obtiene la clase de estrategia para un tipo dado"""
        if strategy_type not in cls._strategies:
            available = [st.value for st in cls._strategies.keys()]
            raise ValueError(f"Strategy type '{strategy_type.value}' not registered. Available: {available}")
        
        return cls._strategies[strategy_type]
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Obtiene lista de estrategias disponibles"""
        return list(cls._strategies.keys())
    
    @classmethod
    def is_registered(cls, strategy_type: ExtractionStrategyType) -> bool:
        """Verifica si una estrategia está registrada"""
        return strategy_type in cls._strategies

# Auto-registrar estrategias disponibles
def register_default_strategies():
    """Registra las estrategias por defecto"""
    try:
        from ..implementations.full_load import FullLoadStrategy
        from ..implementations.incremental import IncrementalStrategy
        from ..implementations.time_range import TimeRangeStrategy
        
        strategies_registered = []
        StrategyRegistry.register(ExtractionStrategyType.FULL_LOAD, FullLoadStrategy)
        strategies_registered.append("full")
        StrategyRegistry.register(ExtractionStrategyType.INCREMENTAL, IncrementalStrategy)
        strategies_registered.append("incremental")
        StrategyRegistry.register(ExtractionStrategyType.TIME_RANGE, TimeRangeStrategy)
        strategies_registered.append("time_range")
        
        # Un solo mensaje resumido con todas las estrategias
        logger.debug(f"Estrategias registradas: {', '.join(strategies_registered)}")
    except ImportError as e:
        logger.warning(f"No se pudieron registrar algunas estrategias por defecto: {e}")

# Registrar automáticamente al importar
register_default_strategies()