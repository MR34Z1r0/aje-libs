# strategies/registry/strategy_registry.py
from typing import Dict, Type, Optional, Callable
from ..base.extraction_strategy import ExtractionStrategy
from ..base.strategy_types import ExtractionStrategyType
from ....shared.services.logging import LoggerService

logger = LoggerService.get_logger(__name__)


class StrategyRegistry:
    """
    Registro central de estrategias de extracción (OCP - extensible sin modificar)
    Permite registro dinámico y desacoplado de estrategias
    """
    
    _strategies: Dict[ExtractionStrategyType, Type[ExtractionStrategy]] = {}
    _validation_callbacks: Dict[ExtractionStrategyType, Callable] = {}
    
    @classmethod
    def register(
        cls, 
        strategy_type: ExtractionStrategyType, 
        strategy_class: Type[ExtractionStrategy],
        validator: Optional[Callable[[Type[ExtractionStrategy]], bool]] = None
    ):
        """
        Registra una nueva estrategia con validación opcional
        
        Args:
            strategy_type: Tipo de estrategia a registrar
            strategy_class: Clase de la estrategia que debe heredar de ExtractionStrategy
            validator: Función opcional para validar la estrategia antes de registrarla
            
        Raises:
            ValueError: Si la estrategia no es válida o el tipo ya está registrado
            TypeError: Si la clase no hereda de ExtractionStrategy
        """
        # Validar que la clase herede de ExtractionStrategy
        if not issubclass(strategy_class, ExtractionStrategy):
            raise TypeError(
                f"La clase '{strategy_class.__name__}' debe heredar de ExtractionStrategy"
            )
        
        # Validación personalizada si se proporciona
        if validator and not validator(strategy_class):
            raise ValueError(
                f"Validación fallida para estrategia '{strategy_class.__name__}' de tipo '{strategy_type.value}'"
            )
        
        # Validación básica: verificar que tenga los métodos requeridos
        required_methods = ['build_extraction_params', 'validate', 'get_strategy_type', 'validate_and_cache']
        missing_methods = [m for m in required_methods if not hasattr(strategy_class, m)]
        if missing_methods:
            raise ValueError(
                f"La estrategia '{strategy_class.__name__}' no implementa los métodos requeridos: {missing_methods}"
            )
        
        # Registrar la estrategia
        cls._strategies[strategy_type] = strategy_class
        
        # Registrar validator si se proporciona
        if validator:
            cls._validation_callbacks[strategy_type] = validator
        
        logger.debug(f"✅ Estrategia registrada: {strategy_type.value} -> {strategy_class.__name__}")
    
    @classmethod
    def register_with_name(
        cls,
        strategy_name: str,
        strategy_class: Type[ExtractionStrategy],
        validator: Optional[Callable[[Type[ExtractionStrategy]], bool]] = None
    ):
        """
        Registra una estrategia usando su nombre (string) - más conveniente para uso dinámico
        
        Args:
            strategy_name: Nombre de la estrategia (ej: 'full', 'incremental', 'time_range')
            strategy_class: Clase de la estrategia
            validator: Función opcional para validar la estrategia
        """
        try:
            strategy_type = ExtractionStrategyType.from_string(strategy_name)
            cls.register(strategy_type, strategy_class, validator)
        except ValueError as e:
            raise ValueError(
                f"No se pudo registrar estrategia con nombre '{strategy_name}': {e}"
            )
    
    @classmethod
    def unregister(cls, strategy_type: ExtractionStrategyType):
        """
        Desregistra una estrategia
        
        Args:
            strategy_type: Tipo de estrategia a desregistrar
        """
        if strategy_type in cls._strategies:
            strategy_class = cls._strategies.pop(strategy_type)
            cls._validation_callbacks.pop(strategy_type, None)
            logger.debug(f"🗑️ Estrategia desregistrada: {strategy_type.value} -> {strategy_class.__name__}")
        else:
            logger.warning(f"⚠️ Intento de desregistrar estrategia no registrada: {strategy_type.value}")
    
    @classmethod
    def get_strategy_class(cls, strategy_type: ExtractionStrategyType) -> Type[ExtractionStrategy]:
        """
        Obtiene la clase de estrategia para un tipo dado
        
        Args:
            strategy_type: Tipo de estrategia
            
        Returns:
            Clase de estrategia
            
        Raises:
            ValueError: Si la estrategia no está registrada
        """
        if strategy_type not in cls._strategies:
            available = [st.value for st in cls._strategies.keys()]
            raise ValueError(
                f"Strategy type '{strategy_type.value}' not registered. "
                f"Available: {available}"
            )
        
        return cls._strategies[strategy_type]
    
    @classmethod
    def create(
        cls,
        strategy_type: ExtractionStrategyType,
        table_config,
        extraction_config,
        watermark_storage=None,
        **kwargs
    ) -> ExtractionStrategy:
        """
        Crea una instancia de estrategia directamente desde el registro
        
        Args:
            strategy_type: Tipo de estrategia
            table_config: Configuración de tabla
            extraction_config: Configuración de extracción
            watermark_storage: Storage de watermarks (opcional)
            **kwargs: Argumentos adicionales para el constructor
            
        Returns:
            Instancia de la estrategia
        """
        strategy_class = cls.get_strategy_class(strategy_type)
        return strategy_class(table_config, extraction_config, watermark_storage, **kwargs)
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Obtiene lista de estrategias disponibles"""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_available_strategy_names(cls) -> list:
        """Obtiene lista de nombres de estrategias disponibles"""
        return [st.value for st in cls._strategies.keys()]
    
    @classmethod
    def is_registered(cls, strategy_type: ExtractionStrategyType) -> bool:
        """Verifica si una estrategia está registrada"""
        return strategy_type in cls._strategies
    
    @classmethod
    def clear(cls):
        """Limpia todas las estrategias registradas (útil para tests)"""
        cls._strategies.clear()
        cls._validation_callbacks.clear()
        logger.debug("🗑️ Todas las estrategias han sido desregistradas")
    
    @classmethod
    def get_registry_info(cls) -> Dict[str, any]:
        """Obtiene información sobre el registro de estrategias"""
        return {
            'registered_count': len(cls._strategies),
            'strategies': {
                st.value: cls._strategies[st].__name__
                for st in cls._strategies.keys()
            },
            'available_types': cls.get_available_strategy_names()
        }

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