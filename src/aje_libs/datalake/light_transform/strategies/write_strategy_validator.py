# -*- coding: utf-8 -*-
"""
WriteStrategyValidator - Validador de requisitos para estrategias de escritura
Verifica que las estrategias tengan todos los requisitos necesarios antes de ejecutarse
"""
from typing import List, Optional, Dict, Any
from ..contracts.storage.write_strategy_interface import IWriteStrategy
from ...shared.models import ColumnMetadata
from ...shared.services.logging import LoggerService


class WriteStrategyValidator:
    """
    Validador de requisitos para estrategias de escritura.
    Verifica columnas ID, columnas de período, existencia de tablas, etc.
    """
    
    def __init__(self, logger=None):
        """
        Inicializa el validador
        
        Args:
            logger: Logger (opcional)
        """
        self.logger = logger or LoggerService.get_logger(__name__)
    
    def validate_strategy_requirements(
        self,
        write_strategy: IWriteStrategy,
        columns_metadata: List[ColumnMetadata],
        table_exists: bool,
        df=None
    ) -> Dict[str, Any]:
        """
        Valida que una estrategia tenga todos los requisitos necesarios
        
        Args:
            write_strategy: Estrategia a validar
            columns_metadata: Metadatos de columnas
            table_exists: Si la tabla destino existe
            df: DataFrame (opcional, para validaciones adicionales)
            
        Returns:
            Dict con información de validación:
                - valid: Si la estrategia es válida
                - warnings: Lista de advertencias
                - errors: Lista de errores
                - metadata: Información adicional (id_columns, period_column, etc.)
        """
        result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'metadata': {}
        }
        
        strategy_name = write_strategy.get_strategy_name()
        
        # Validar requisitos según el tipo de estrategia
        if strategy_name == 'incremental':
            result = self._validate_incremental(
                write_strategy,
                columns_metadata,
                table_exists,
                df,
                result
            )
        elif strategy_name == 'time_range':
            result = self._validate_time_range(
                write_strategy,
                columns_metadata,
                table_exists,
                df,
                result
            )
        elif strategy_name == 'full_load':
            result = self._validate_full_load(
                write_strategy,
                columns_metadata,
                table_exists,
                df,
                result
            )
        
        # Resumir validación
        if result['errors']:
            result['valid'] = False
            self.logger.error(
                f"❌ Validación fallida para estrategia '{strategy_name}': {result['errors']}"
            )
        elif result['warnings']:
            self.logger.warning(
                f"⚠️ Advertencias para estrategia '{strategy_name}': {result['warnings']}"
            )
        else:
            self.logger.debug(f"✅ Validación exitosa para estrategia '{strategy_name}'")
        
        return result
    
    def _validate_incremental(
        self,
        write_strategy: IWriteStrategy,
        columns_metadata: List[ColumnMetadata],
        table_exists: bool,
        df,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida requisitos para estrategia incremental"""
        # Buscar columnas ID
        id_columns = [col.name for col in columns_metadata if getattr(col, 'is_id', False)]
        result['metadata']['id_columns'] = id_columns
        
        # Validar columnas ID en DataFrame si está disponible
        if df is not None and id_columns:
            missing_id_cols = [col for col in id_columns if col not in df.columns]
            if missing_id_cols:
                result['warnings'].append(
                    f"Columnas ID faltantes en DataFrame: {missing_id_cols}. "
                    f"Se usará APPEND en lugar de MERGE."
                )
        
        # Advertencia si no hay columnas ID pero la tabla existe
        if not id_columns and table_exists:
            result['warnings'].append(
                "No se encontraron columnas ID marcadas (is_id=true). "
                "Se usará APPEND en lugar de MERGE para carga incremental."
            )
        
        # Información útil
        if id_columns:
            result['metadata']['can_use_merge'] = table_exists and df is not None
        else:
            result['metadata']['can_use_merge'] = False
        
        return result
    
    def _validate_time_range(
        self,
        write_strategy: IWriteStrategy,
        columns_metadata: List[ColumnMetadata],
        table_exists: bool,
        df,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida requisitos para estrategia time_range"""
        # Buscar columna de período
        period_column = None
        
        # Buscar por atributo is_process_period
        for col in columns_metadata:
            if getattr(col, 'is_process_period', False):
                period_column = col.name
                break
        
        # Si no se encuentra, buscar por patrones de nombre
        if not period_column:
            period_patterns = ['process_period', 'periodo', 'period', 'fecha_proceso', 'processperiod']
            for col in columns_metadata:
                col_name_lower = col.name.lower()
                for pattern in period_patterns:
                    if pattern in col_name_lower:
                        period_column = col.name
                        result['warnings'].append(
                            f"Columna de período '{period_column}' encontrada por nombre "
                            f"(no marcada como is_process_period). "
                            f"Considere marcar la columna en columns.csv."
                        )
                        break
                if period_column:
                    break
        
        result['metadata']['period_column'] = period_column
        
        # Validar que la columna exista en DataFrame
        if df is not None and period_column:
            if period_column not in df.columns:
                result['errors'].append(
                    f"La columna de período '{period_column}' no existe en el DataFrame. "
                    f"Columnas disponibles: {list(df.columns)}"
                )
        
        # Error si no se encuentra columna de período
        if not period_column:
            result['errors'].append(
                "No se encontró columna de período para estrategia time_range. "
                "Marque una columna con is_process_period=true en columns.csv o "
                "asegúrese de que el nombre de la columna contenga 'process_period', 'periodo', 'period', etc."
            )
        
        return result
    
    def _validate_full_load(
        self,
        write_strategy: IWriteStrategy,
        columns_metadata: List[ColumnMetadata],
        table_exists: bool,
        df,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida requisitos para estrategia full_load"""
        # Full load no tiene requisitos especiales, pero validar DataFrame
        if df is not None:
            record_count = df.count()
            result['metadata']['record_count'] = record_count
            
            if record_count == 0:
                result['warnings'].append(
                    "DataFrame vacío para full load. Se sobrescribirá la tabla con una tabla vacía."
                )
        
        return result


__all__ = ['WriteStrategyValidator']

