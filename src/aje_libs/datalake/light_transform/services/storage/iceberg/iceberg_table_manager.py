# -*- coding: utf-8 -*-
"""
IcebergTableManager - Utilidades y helpers para operaciones Apache Iceberg.
Proporciona funcionalidades auxiliares como TimeRangeDeleteManager.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger


class TimeRangeDeleteManager:
    """
    Manager para manejar el DELETE de registros de un período específico
    antes de hacer APPEND de nuevos datos en Apache Iceberg.
    
    Esta clase encapsula la lógica específica de Iceberg para operaciones
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
        iceberg_table_path: str,
        period_column: str,
        period_values: List[Any],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Elimina registros de un período específico de una tabla Iceberg
        
        Args:
            iceberg_table_path: Ruta de la tabla Iceberg (formato: catalog.database.table o path)
            period_column: Columna que define el período
            period_values: Lista de valores del período a eliminar
            additional_filters: Filtros adicionales (opcional)
            
        Returns:
            Número de registros eliminados
            
        Raises:
            Exception: Si hay error al eliminar los datos
        """
        try:
            # Parsear nombre de tabla
            table_name = self._parse_table_name(iceberg_table_path)
            
            # Verificar si la tabla existe
            if not self._table_exists(table_name):
                self.logger.warning(f"La tabla Iceberg {iceberg_table_path} no existe aún. No hay datos para eliminar.")
                return 0
            
            # Obtener conteo antes del DELETE
            count_before = self.spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name}").first()['cnt']
            self.logger.info(f"Registros antes del DELETE: {count_before}")
            
            # Construir condición DELETE
            values_str = ', '.join([f"'{val}'" for val in period_values])
            delete_condition = f"{period_column} IN ({values_str})"
            
            if additional_filters:
                for col_name, col_value in additional_filters.items():
                    if isinstance(col_value, str):
                        delete_condition += f" AND {col_name} = '{col_value}'"
                    else:
                        delete_condition += f" AND {col_name} = {col_value}"
            
            self.logger.info(f"Ejecutando DELETE en Iceberg con condición: {delete_condition}")
            
            # Ejecutar DELETE
            delete_sql = f"DELETE FROM {table_name} WHERE {delete_condition}"
            self.spark.sql(delete_sql)
            
            # Obtener conteo después del DELETE
            count_after = self.spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name}").first()['cnt']
            deleted_count = count_before - count_after
            
            self.logger.info(f"DELETE en Iceberg completado. Registros eliminados: {deleted_count}")
            self.logger.info(f"Registros restantes: {count_after}")
            
            return deleted_count
            
        except Exception as exc:
            self.logger.error(f"Error al eliminar período {period_values} de columna {period_column} en Iceberg: {exc}")
            raise
    
    def _parse_table_name(self, path: str) -> str:
        """Parsea la ruta a un nombre de tabla válido para Iceberg"""
        # Si es formato catalog.database.table, retornarlo directamente
        if "." in path and not path.startswith("s3://") and not path.startswith("/"):
            return path
        
        # Si es path (s3://bucket/path), convertir a formato de tabla
        return path.replace("s3://", "").replace("/", "_")
    
    def _table_exists(self, table_name: str) -> bool:
        """Verifica si la tabla Iceberg existe"""
        try:
            self.spark.sql(f"SELECT 1 FROM {table_name} LIMIT 1")
            return True
        except Exception:
            return False


__all__ = ["TimeRangeDeleteManager"]

