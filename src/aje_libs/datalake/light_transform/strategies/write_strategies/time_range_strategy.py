# -*- coding: utf-8 -*-
"""
TimeRangeStrategy - Estrategia de escritura para carga por rango de tiempo (DELETE + INSERT)
Aplica DELETE + INSERT para tablas con load_type='time_range' o 'between-date'
"""
from typing import Any, Dict, List, Optional

from ...contracts.storage.write_strategy_interface import IWriteStrategy
from ....shared.services.logging import LoggerService


class TimeRangeStrategy(IWriteStrategy):
    """
    Estrategia para carga por rango de tiempo.
    Ejecuta DELETE de períodos específicos seguido de INSERT de nuevos datos.
    """
    
    def __init__(self):
        """Inicializa la estrategia time_range"""
        self.logger = LoggerService.get_logger(__name__)
    
    def execute(
        self,
        data_writer,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Ejecuta operación DELETE + INSERT usando write_time_range
        
        Args:
            data_writer: Instancia de IDataWriter
            df: DataFrame con los datos
            path: Ruta de destino
            partition_cols: Columnas de partición
            **kwargs: Argumentos adicionales:
                - period_column: Columna que define el período (requerido)
                - period_values: Lista de valores del período a eliminar (opcional, se extrae de df si no se proporciona)
                - additional_filters: Filtros adicionales para DELETE (opcional)
                - time_range_config: Configuración completa de time_range (opcional, se construye si no se proporciona)
                
        Raises:
            ValueError: Si period_column no está disponible o si no hay datos para procesar
        """
        # Validación básica
        if df is None or df.isEmpty():
            self.logger.warning("⚠️ DataFrame vacío para estrategia time_range - saltando escritura")
            return
        
        time_range_config = kwargs.get('time_range_config')
        period_column = kwargs.get('period_column')
        period_values = kwargs.get('period_values')
        additional_filters = kwargs.get('additional_filters')
        
        # Construir time_range_config si no se proporciona
        if not time_range_config:
            if not period_column:
                raise ValueError(
                    "period_column es requerido para TimeRangeStrategy. "
                    "Proporciona 'period_column' en kwargs o inclúyelo en 'time_range_config'. "
                    "Asegúrate de que la columna esté marcada como is_process_period en columns.csv."
                )
            
            # Validar que period_column exista en el DataFrame
            if period_column not in df.columns:
                raise ValueError(
                    f"La columna de período '{period_column}' no existe en el DataFrame. "
                    f"Columnas disponibles: {list(df.columns)}"
                )
            
            # Si no se proporcionan period_values, extraerlos del DataFrame
            if not period_values:
                try:
                    period_values = [
                        row[period_column] 
                        for row in df.select(period_column).distinct().collect()
                    ]
                    if not period_values:
                        self.logger.warning(
                            f"⚠️ No se encontraron valores únicos en la columna '{period_column}'. "
                            f"Usando APPEND como fallback."
                        )
                        data_writer.append(df=df, path=path, partition_cols=partition_cols)
                        return
                except Exception as e:
                    raise ValueError(
                        f"No se pudieron extraer period_values de la columna '{period_column}': {e}"
                    )
            
            time_range_config = {
                'period_column': period_column,
                'period_values': period_values,
            }
            
            if additional_filters:
                time_range_config['additional_filters'] = additional_filters
        
        records_count = df.count()
        periods_info = f"{time_range_config.get('period_column')}={time_range_config.get('period_values')}"
        self.logger.info(
            f"⏰ Ejecutando TIME_RANGE (DELETE + INSERT): {records_count} registros para períodos: {periods_info}"
        )
        
        data_writer.write_time_range(
            df=df,
            path=path,
            partition_cols=partition_cols,
            time_range_config=time_range_config
        )
        
        self.logger.info(
            f"✅ TIME_RANGE completado: DELETE de períodos {periods_info} + INSERT de {records_count} registros"
        )
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia"""
        return "time_range"
    
    def requires_id_columns(self) -> bool:
        """Esta estrategia no requiere columnas ID"""
        return False
    
    def requires_period_column(self) -> bool:
        """Esta estrategia requiere columna de período"""
        return True


__all__ = ["TimeRangeStrategy"]

