# strategies/strategy_factory_v2.py
from typing import Optional
from ..strategies.base.extraction_strategy import ExtractionStrategy
from ..strategies.base.strategy_types import ExtractionStrategyType
from ..strategies.registry.strategy_registry import StrategyRegistry
from ..contracts.strategy_interface import IExtractionStrategy
from ...shared.contracts.watermark import IWatermarkStorage
from ..models.table_config import TableConfig
from ..models.extraction_config import ExtractionConfig
from aje_libs.datalake.shared.exceptions import ConfigurationException as ConfigurationError
from ...shared.services.logging import LoggerService

logger = LoggerService.get_logger(__name__)

class StrategyFactory:
    """Factory simplificado para crear estrategias de extracción"""
    
    @classmethod
    def create(cls, table_config: TableConfig, extraction_config: ExtractionConfig,
               watermark_storage: IWatermarkStorage = None) -> IExtractionStrategy:
        """Crea la estrategia apropiada basada en configuración"""
        
        # Determinar tipo de estrategia
        strategy_type = cls._determine_strategy_type(table_config, extraction_config)
        logger.debug(f"Strategy Factory - Table: {extraction_config.table_name}, Type: {strategy_type.value}")
        
        # Verificar que esté registrada
        if not StrategyRegistry.is_registered(strategy_type):
            available = [st.value for st in StrategyRegistry.get_available_strategies()]
            error_msg = f"Strategy type '{strategy_type.value}' not registered. Available: {available}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # Crear instancia de la nueva estrategia
        strategy_class = StrategyRegistry.get_strategy_class(strategy_type)
        new_strategy = strategy_class(table_config, extraction_config, watermark_storage)
        
        # Validar configuración
        if not new_strategy.validate_and_cache():
            error_msg = f"Strategy validation failed for {strategy_class.__name__}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # Envolver en adaptador para compatibilidad
        from ..strategies.adapters.strategy_adapter import StrategyAdapter
        strategy_adapter = StrategyAdapter(new_strategy)
        
        return strategy_adapter
    
    @classmethod
    def _determine_strategy_type(cls, table_config: TableConfig, 
                            extraction_config: ExtractionConfig) -> ExtractionStrategyType:
        """Determina qué estrategia usar basada en configuración"""
        
        # Usar load_type de configuración
        load_type = table_config.load_type.lower().strip() if table_config.load_type else 'full'
        logger.debug(f"Load type desde config: '{load_type}'")
        
        # Lógica específica para determinar estrategia
        if load_type in ['incremental']:
            # Verificar si tiene los campos necesarios para incremental
            has_incremental_config = (
                (hasattr(table_config, 'filter_column') and table_config.filter_column) or
                (hasattr(table_config, 'partition_column') and table_config.partition_column)
            )
            
            if has_incremental_config:
                logger.debug("Configuración incremental detectada - usando estrategia INCREMENTAL")
                return ExtractionStrategyType.INCREMENTAL
            else:
                logger.warning("load_type incremental pero falta configuración - usando FULL_LOAD")
                return ExtractionStrategyType.FULL_LOAD
        
        elif load_type in ['date_range', 'between-date', 'time_range']:
            # Verificar si tiene configuración para time range
            has_time_range_config = (
                hasattr(table_config, 'filter_column') and table_config.filter_column and
                ((hasattr(table_config, 'start_value') and table_config.start_value and
                hasattr(table_config, 'end_value') and table_config.end_value) or
                (hasattr(table_config, 'delay_incremental_ini') and table_config.delay_incremental_ini))
            )
            
            if has_time_range_config:
                logger.debug(f"Configuración time_range detectada para '{load_type}' - usando estrategia TIME_RANGE")
                return ExtractionStrategyType.TIME_RANGE
            else:
                logger.warning(f"load_type '{load_type}' pero falta configuración - usando FULL_LOAD")
                return ExtractionStrategyType.FULL_LOAD
        
        # Default a full load
        try:
            strategy_type = ExtractionStrategyType.from_string(load_type)
            logger.debug(f"Estrategia mapeada: {strategy_type.value}")
            return strategy_type
        except ValueError as e:
            logger.warning(f"No se pudo mapear load_type '{load_type}': {e}")
            logger.debug("Usando estrategia FULL_LOAD por defecto")
            return ExtractionStrategyType.FULL_LOAD
    
    @classmethod
    def get_supported_strategies(cls) -> list:
        """Obtiene lista de estrategias soportadas"""
        return [st.value for st in StrategyRegistry.get_available_strategies()]
    
    @classmethod
    def validate_partition_mode(cls, table_config: TableConfig, extraction_config: ExtractionConfig):
        """🆕 NUEVO MÉTODO: Valida la configuración de PARTITION_MODE"""
        
        partition_mode = getattr(table_config, 'partition_mode', 'AUTO').upper()
        
        # Validar que PARTITION_MODE solo se use con FULL o TIME_RANGE
        if partition_mode != 'AUTO' and table_config.load_type not in ['full', 'time_range']:
            logger.warning(f"PARTITION_MODE={partition_mode} ignored for load_type={table_config.load_type}")
        
        # Validar que MIN_MAX tenga PARTITION_COLUMN
        if partition_mode == 'MIN_MAX':
            if not (hasattr(table_config, 'partition_column') and table_config.partition_column):
                raise ValueError(f"PARTITION_MODE=MIN_MAX requires PARTITION_COLUMN to be configured")
        
        logger.info(f"✅ PARTITION_MODE validation passed: {partition_mode}")