# strategies/implementations/full_load.py
from typing import List
from ..base.extraction_strategy import ExtractionStrategy
from ..base.extraction_params import ExtractionParams
from ..base.strategy_types import ExtractionStrategyType
from ....shared.services.logging import LoggerService
from aje_libs.datalake.shared.models import LoadMode

logger = LoggerService.get_logger(__name__)

class FullLoadStrategy(ExtractionStrategy):
    """Estrategia para carga completa - simple y directa"""
    
    def get_strategy_type(self) -> ExtractionStrategyType:
        return ExtractionStrategyType.FULL_LOAD
    
    def build_extraction_params(self) -> ExtractionParams:
        logger.debug(f"Full Load Strategy - Table: {self.extraction_config.table_name}, Mode: {self.extraction_config.load_mode.value}")
        
        # 🔄 RESET mode: El cleanup ya fue realizado por el orchestrator
        if self.extraction_config.load_mode == LoadMode.RESET:
            logger.debug("RESET mode - cleanup already performed")

        # 🆕 INITIAL mode: mensaje explícito para consistencia de logs
        if self.extraction_config.load_mode == LoadMode.INITIAL:
            logger.info("🆕 INITIAL mode - full load; watermark only if table is incremental")

        # 🎯 Determinar si debe trackear watermark
        should_track_watermark = self._should_track_watermark()
        
        if should_track_watermark:
            logger.info("✅ Full load will track watermark")
        else:
            logger.debug("Full load without watermark tracking")
        
        # Detectar si necesita particionado
        if self._should_use_partitioned_load_with_mode():  # 🔄 CAMBIO
            logger.info("⚠️ Partitioned full load detected")
            return self._build_partitioned_params(should_track_watermark)
        
        # Carga no particionada
        logger.debug("Building non-partitioned full load params")
        
        metadata = self._build_basic_metadata()
        
        # Marcar si debe rastrear watermark
        if should_track_watermark:
            metadata['should_track_watermark'] = True
            metadata['watermark_column'] = self.table_config.partition_column
            logger.info(f"📊 Watermark tracking enabled for: {self.table_config.partition_column}")
        
        params = ExtractionParams(
            table_name=self._get_source_table_name(),
            columns=self._parse_columns(),
            metadata=metadata
        )
        
        # Agregar filtros básicos
        basic_filters = self._build_basic_filters()
        for filter_condition in basic_filters:
            if filter_condition:
                params.add_where_condition(filter_condition)
                logger.debug(f"Added filter: {filter_condition}")
        
        logger.info(f"✅ Params built - Columns: {len(params.columns)}, Filters: {len(params.where_conditions)}")
        return params
    
    def _should_use_partitioned_load_with_mode(self) -> bool:
        """🆕 MÉTODO MODIFICADO: Evalúa particionado según PARTITION_MODE"""
        partition_mode = getattr(self.table_config, 'partition_mode', 'AUTO').upper()
        
        if partition_mode == 'MIN_MAX':
            # Forzar particionado
            if not self._has_valid_partition_column():
                raise ValueError("PARTITION_MODE=MIN_MAX requires PARTITION_COLUMN")
            return True
            
        elif partition_mode == 'NONE':
            # Nunca particionar
            return False
            
        else:  # AUTO
            # Usar lógica existente
            return self._should_use_partitioned_load()
    
    def _has_valid_partition_column(self) -> bool:
        """🆕 NUEVO MÉTODO"""
        return (
            hasattr(self.table_config, 'partition_column') and 
            self.table_config.partition_column and 
            self.table_config.partition_column.strip() != ''
        )

    def _should_track_watermark(self) -> bool:
        """
        Determina si debe guardar watermark después de esta carga.
        
        TRUE cuando:
        - Es modo INITIAL o RESET
        - Tiene partition_column configurado
        - Tiene watermark storage disponible
        - La tabla está configurada para incremental
        """
        
        has_partition_column = (
            hasattr(self.table_config, 'partition_column') and 
            self.table_config.partition_column and 
            self.table_config.partition_column.strip()
        )
        
        has_watermark_storage = self.watermark_storage is not None
        
        is_incremental_table = (
            hasattr(self.table_config, 'load_type') and
            self.table_config.load_type and
            self.table_config.load_type.lower() == 'incremental'
        )
        
        load_mode = self.extraction_config.load_mode
        
        # Solo trackear en INITIAL o RESET
        should_track = (
            load_mode in [LoadMode.INITIAL, LoadMode.RESET] and
            has_partition_column and
            has_watermark_storage and
            is_incremental_table
        )
        
        logger.debug(f"Watermark tracking - Mode: {load_mode.value}, "
                    f"has_partition: {has_partition_column}, has_storage: {has_watermark_storage}, "
                    f"is_incremental: {is_incremental_table}, should_track: {should_track}")
        
        return should_track
    
    def _reset_watermark_if_exists(self):
        """Limpia el watermark existente en modo RESET"""
        if not self.watermark_storage:
            logger.info("No watermark storage - skip reset")
            return
        
        if not (hasattr(self.table_config, 'partition_column') and 
                self.table_config.partition_column):
            logger.info("No partition column - skip reset")
            return
        
        try:
            # Verificar si existe watermark antes de intentar eliminar
            existing_watermark = self.watermark_storage.get_last_extracted_value(
                table_name=self.table_config.stage_table_name,
                column_name=self.table_config.partition_column
            )
            
            if existing_watermark:
                logger.info(f"🗑️ Found existing watermark: {existing_watermark}")
                
                # Si el storage soporta delete, usarlo
                if hasattr(self.watermark_storage, 'delete_watermark'):
                    self.watermark_storage.delete_watermark(
                        table_name=self.table_config.stage_table_name,
                        column_name=self.table_config.partition_column
                    )
                    logger.info(f"✅ Watermark deleted for {self.table_config.stage_table_name}")
                else:
                    logger.warning("Watermark storage does not support delete operation")
            else:
                logger.info("No existing watermark to reset")
                
        except Exception as e:
            logger.warning(f"Failed to reset watermark: {e}")
    
    def _should_use_partitioned_load(self) -> bool:
        """Detecta si la tabla requiere particionado"""
        return (
            hasattr(self.table_config, 'source_table_type') and 
            self.table_config.source_table_type == 't' and
            hasattr(self.table_config, 'partition_column') and 
            self.table_config.partition_column and 
            self.table_config.partition_column.strip() != ''
        )

    def _build_partitioned_params(self, should_track_watermark: bool = False) -> ExtractionParams:
        """
        Construye parámetros especiales para carga particionada
        
        Args:
            should_track_watermark: Si debe rastrear watermark durante esta carga completa
            
        Returns:
            ExtractionParams configurado para particionado
        """
        logger.info("🔧 Building partitioned params for full load")
        
        # Construir table_name con JOIN para particionado
        table_name_with_joins = f"{self.table_config.source_schema}.{self.table_config.source_table}"
        
        if hasattr(self.table_config, 'join_expr') and self.table_config.join_expr and self.table_config.join_expr.strip():
            table_name_with_joins += f" {self.table_config.join_expr.strip()}"
            logger.info(f"📎 Table with JOIN: {table_name_with_joins}")
        
        # Construir metadata completo
        metadata = {
            **self._build_basic_metadata(),
            'needs_partitioning': True,
            'partition_column': self.table_config.partition_column,
            'source_table_type': self.table_config.source_table_type,
            'chunk_size': self.extraction_config.chunk_size
        }
        
        # 🔑 Agregar watermark tracking si es necesario
        if should_track_watermark:
            metadata['should_track_watermark'] = True
            metadata['watermark_column'] = self.table_config.partition_column
            logger.info(f"📊 Partitioned load will track watermark for column: {self.table_config.partition_column}")
        else:
            logger.info(f"ℹ️ Partitioned load without watermark tracking")
        
        # Crear params
        params = ExtractionParams(
            table_name=table_name_with_joins,
            columns=self._parse_columns(),
            metadata=metadata
        )
        
        # Agregar filtros básicos (FILTER_EXP, sin fechas hardcodeadas)
        basic_filters = self._build_basic_filters()
        for filter_condition in basic_filters:
            if filter_condition:  # Solo agregar si no está vacío
                params.add_where_condition(filter_condition)
                logger.debug(f"Added filter: {filter_condition}")
        
        logger.info(f"✅ Partitioned params built successfully")
        return params

    def _should_use_partitioned_load(self) -> bool:
        """Detecta si la tabla requiere particionado"""
        return (
            hasattr(self.table_config, 'source_table_type') and 
            self.table_config.source_table_type == 't' and
            hasattr(self.table_config, 'partition_column') and 
            self.table_config.partition_column and 
            self.table_config.partition_column.strip() != ''
        )

    def validate(self) -> bool:
        """Valida configuración para carga completa"""
        # Campos requeridos básicos
        required_fields = [
            ('stage_table_name', self.table_config.stage_table_name),
            ('source_schema', self.table_config.source_schema),
            ('source_table', self.table_config.source_table),
            ('columns', self.table_config.columns)
        ]
        
        validation_errors = []
        for field_name, field_value in required_fields:
            # Solo loguear en DEBUG o si hay error
            logger.debug(f"Validating {field_name}")
            
            if field_value is None:
                validation_errors.append(f"{field_name} is None")
            elif not str(field_value).strip():
                validation_errors.append(f"{field_name} is empty")
        
        if validation_errors:
            logger.error(f"❌ Validation failed: {', '.join(validation_errors)}")
            return False
        
        # Validación exitosa - no loguear, es el caso normal
        return True
    
    def estimate_resources(self) -> dict:
        """Estima recursos para carga completa"""
        base_estimate = super().estimate_resources()
        
        # Full loads pueden ser más intensivos
        base_estimate.update({
            'estimated_memory_mb': 1000,
            'supports_chunking': self._should_use_chunking(),
            'parallel_safe': True
        })
        
        return base_estimate
    
    def _build_basic_filters(self) -> List[str]:
        """Construye SOLO filtros básicos (FILTER_EXP)"""
        filters = []
        
        if hasattr(self.table_config, 'filter_exp') and self.table_config.filter_exp:
            clean_filter = self.table_config.filter_exp.replace('"', '').strip()
            if clean_filter:
                filters.append(clean_filter)
        
        return filters
    
    def _build_simple_date_filter(self) -> str:
        """Construye un filtro de fecha simple"""
        try:
            from utils.date_utils import get_date_limits
            
            # Limpiar delay value
            clean_delay = self.table_config.delay_incremental_ini.strip().replace("'", "")
            
            # Obtener límites de fecha
            lower_limit, upper_limit = get_date_limits(
                clean_delay,
                getattr(self.table_config, 'filter_data_type', '') or ""
            )
            
            # Construir condición de filtro
            filter_condition = self.table_config.filter_column.replace(
                '{0}', lower_limit
            ).replace(
                '{1}', upper_limit
            ).replace('"', '')
            
            return filter_condition
            
        except Exception as e:
            logger.warning(f"Failed to build date filter: {e}")
            return None
    
    def _should_use_chunking(self) -> bool:
        """Determina si debería usar chunking"""
        return (
            hasattr(self.table_config, 'partition_column') and 
            self.table_config.partition_column and 
            self.table_config.partition_column.strip() != '' and
            getattr(self.table_config, 'source_table_type', '') == 't'
        )
    
    def _get_chunking_column(self) -> str:
        """Obtiene la columna para chunking"""
        if hasattr(self.table_config, 'partition_column') and self.table_config.partition_column:
            return self.table_config.partition_column.strip()
        
        if hasattr(self.table_config, 'id_column') and self.table_config.id_column:
            return self.table_config.id_column.strip()
        
        return None