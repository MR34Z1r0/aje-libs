"""
Servicios de escritura y manejo de tablas Delta.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from delta.tables import DeltaTable

from aje_libs.datalake.shared.contracts.storage import IDataWriter
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger


class TimeRangeDeleteManager:
    """
    Clase para manejar el DELETE de registros de un período específico
    antes de hacer APPEND de nuevos datos
    """

    def __init__(self, spark, logger=None):
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)

    def delete_period_data(
        self,
        delta_table_path: str,
        period_column: str,
        period_values: List[Any],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        try:
            if not DeltaTable.isDeltaTable(self.spark, delta_table_path):
                self.logger.warning(f"La tabla {delta_table_path} no existe aún. No hay datos para eliminar.")
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

            self.logger.info(f"Ejecutando DELETE con condición: {delete_condition}")

            delta_table.delete(condition=delete_condition)

            count_after = delta_table.toDF().count()
            deleted_count = count_before - count_after

            self.logger.info(f"DELETE completado. Registros eliminados: {deleted_count}")
            self.logger.info(f"Registros restantes: {count_after}")

            return deleted_count

        except Exception as exc:
            self.logger.error(f"Error al eliminar período {period_values} de columna {period_column}: {exc}")
            raise


class DeltaTableWriter(IDataWriter):
    """Implementación de IDataWriter basada en Delta Lake."""

    def __init__(self, spark, logger=None):
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.delete_manager = TimeRangeDeleteManager(spark, self.logger)

    def overwrite(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        self._write(df, path, mode="overwrite", partition_cols=partition_cols)

    def append(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        self._write(df, path, mode="append", partition_cols=partition_cols)

    def merge(self, df, path: str, merge_condition: str, partition_cols: Optional[List[str]] = None) -> None:
        try:
            delta_table = DeltaTable.forPath(self.spark, path)
            (delta_table.alias("old")
             .merge(df.alias("new"), merge_condition)
             .whenMatchedUpdateAll()
             .whenNotMatchedInsertAll()
             .execute())
            self.logger.info(f"✅ Merge completado en {path}")
        except Exception as exc:
            self.logger.error(f"❌ Error en merge: {exc}")
            raise

    def write_time_range(
        self,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        time_range_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not time_range_config:
            raise ValueError("time_range_config es requerido para modo 'time_range'")

        period_column = time_range_config.get('period_column')
        period_values = time_range_config.get('period_values')
        additional_filters = time_range_config.get('additional_filters')

        if not period_column:
            raise ValueError("period_column es requerido en time_range_config")

        self.logger.info("=== MODO TIME_RANGE: DELETE + APPEND ===")
        self.logger.info(f"Período: {period_column} = {period_values}")

        deleted_count = self.delete_manager.delete_period_data(
            delta_table_path=path,
            period_column=period_column,
            period_values=period_values,
            additional_filters=additional_filters
        )

        self.logger.info(f"Iniciando APPEND de {df.count()} registros nuevos")
        self.append(df, path, partition_cols=partition_cols)
        self.logger.info(f"✅ TIME_RANGE completado: {deleted_count} eliminados, {df.count()} insertados")

    def cleanup(self, path: str) -> None:
        try:
            normalized_path = self._normalize_path(path)
            hadoop_conf = self.spark._jsc.hadoopConfiguration()
            uri = self.spark._jvm.java.net.URI(normalized_path)
            fs = self.spark._jvm.org.apache.hadoop.fs.FileSystem.get(uri, hadoop_conf)
            fs_path = self.spark._jvm.org.apache.hadoop.fs.Path(normalized_path)

            if fs.exists(fs_path):
                deleted = fs.delete(fs_path, True)
                if deleted:
                    self.logger.info(f"🧹 Ruta limpiada exitosamente: {path}")
                else:
                    self.logger.warning(f"⚠️ No se pudo eliminar completamente la ruta: {path}")
            else:
                self.logger.info(f"ℹ️ Ruta no encontrada (nada que eliminar): {path}")
        except Exception as exc:
            self.logger.error(f"Error eliminando datos existentes en {path}: {exc}")
            raise

    def _write(self, df, path: str, mode: str, partition_cols: Optional[List[str]] = None) -> None:
        try:
            writer = df.write.format("delta").mode(mode)
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
            writer.save(path)
            self.logger.info(f"✅ Escritura completada en modo {mode} para {path}")
            self._optimize_table(path)
        except Exception as exc:
            self.logger.error(f"Error al escribir en Delta: {exc}")
            raise

    def _optimize_table(self, path: str):
        try:
            if DeltaTable.isDeltaTable(self.spark, path):
                delta_table = DeltaTable.forPath(self.spark, path)
                delta_table.optimize().executeCompaction()
                self.logger.info(f"Tabla optimizada: {path}")
        except Exception as exc:
            self.logger.warning(f"No se pudo optimizar la tabla: {exc}")

    def _normalize_path(self, path: str) -> str:
        if path.startswith("s3://"):
            return "s3a://" + path[5:]
        return path


__all__ = ["TimeRangeDeleteManager", "DeltaTableWriter"]

