# -*- coding: utf-8 -*-
"""
DeltaTableManager - Utilidades y helpers para operaciones Delta Lake.
Proporciona funcionalidades auxiliares como TimeRangeDeleteManager.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from delta.tables import DeltaTable

from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger


class TimeRangeDeleteManager:
    """
    Manager para manejar el DELETE de registros de un período específico
    antes de hacer APPEND de nuevos datos en Delta Lake.
    
    Esta clase encapsula la lógica específica de Delta Lake para operaciones
    de eliminación por rango de tiempo.
    """
    
    def __init__(self, spark, logger=None):
        """
        Inicializa el manager de eliminación por rango
        
        Args:
            spark: SparkSession
            logger: Logger (opcional)
        """
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)
    
    def delete_period_data(
        self,
        delta_table_path: str,
        period_column: str,
        period_values: List[Any],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Elimina registros de un período específico de una tabla Delta Lake
        
        Args:
            delta_table_path: Ruta de la tabla Delta Lake
            period_column: Columna que define el período
            period_values: Lista de valores del período a eliminar
            additional_filters: Filtros adicionales (opcional)
            
        Returns:
            Número de registros eliminados
            
        Raises:
            Exception: Si hay error al eliminar los datos
        """
        try:
            if not DeltaTable.isDeltaTable(self.spark, delta_table_path):
                self.logger.warning(f"La tabla Delta Lake {delta_table_path} no existe aún. No hay datos para eliminar.")
                return 0
            
            delta_table = DeltaTable.forPath(self.spark, delta_table_path)
            
            count_before = delta_table.toDF().count()
            self.logger.info(f"Registros antes del DELETE: {count_before}")
            
            values_str = ', '.join([f"'{val}'" for val in period_values])
            delete_condition = f"{period_column} IN ({values_str})"
            
            if additional_filters:
                for col_name, col_value in additional_filters.items():
                    if isinstance(col_value, str):
                        delete_condition += f" AND {col_name} = '{col_value}'"
                    else:
                        delete_condition += f" AND {col_name} = {col_value}"
            
            self.logger.info(f"Ejecutando DELETE en Delta Lake con condición: {delete_condition}")
            
            delta_table.delete(condition=delete_condition)
            
            count_after = delta_table.toDF().count()
            deleted_count = count_before - count_after
            
            self.logger.info(f"DELETE en Delta Lake completado. Registros eliminados: {deleted_count}")
            self.logger.info(f"Registros restantes: {count_after}")
            
            return deleted_count
            
        except Exception as exc:
            self.logger.error(f"Error al eliminar período {period_values} de columna {period_column} en Delta Lake: {exc}")
            raise


__all__ = ["TimeRangeDeleteManager"]

