# -*- coding: utf-8 -*-
"""
DeltaTableWriter - Implementación de IDataWriter para Delta Lake.
Estructura estándar para compatibilidad con otros formatos (Iceberg, etc.)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from delta.tables import DeltaTable

from aje_libs.datalake.shared.contracts.storage import IDataWriter
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger
from .delta_table_manager import TimeRangeDeleteManager


class DeltaTableWriter(IDataWriter):
    """
    Implementación de IDataWriter basada en Delta Lake.
    Proporciona operaciones CRUD para tablas Delta Lake.
    """
    
    def __init__(self, spark, logger=None):
        """
        Inicializa el writer de Delta Lake
        
        Args:
            spark: SparkSession
            logger: Logger (opcional)
        """
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.delete_manager = TimeRangeDeleteManager(spark, self.logger)
    
    def overwrite(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Sobrescribe datos en la tabla Delta Lake"""
        self._write(df, path, mode="overwrite", partition_cols=partition_cols)
    
    def append(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Inserta datos en modo append a la tabla Delta Lake"""
        self._write(df, path, mode="append", partition_cols=partition_cols)
    
    def merge(self, df, path: str, merge_condition: str, partition_cols: Optional[List[str]] = None) -> None:
        """
        Realiza operaciones de merge/upsert usando MERGE de Delta Lake
        
        Args:
            df: DataFrame con los datos a mergear
            path: Ruta de la tabla Delta Lake
            merge_condition: Condición SQL para el merge (ej: "old.id = new.id")
            partition_cols: Columnas de partición (ignoradas en merge, Delta las gestiona)
        """
        try:
            delta_table = DeltaTable.forPath(self.spark, path)
            (delta_table.alias("old")
             .merge(df.alias("new"), merge_condition)
             .whenMatchedUpdateAll()
             .whenNotMatchedInsertAll()
             .execute())
            self.logger.info(f"✅ Merge completado en {path}")
        except Exception as exc:
            self.logger.error(f"❌ Error en merge Delta Lake: {exc}")
            raise
    
    def write_time_range(
        self,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        time_range_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Operación específica para eliminar por rango y volver a escribir en Delta Lake
        
        Args:
            df: DataFrame con los nuevos datos
            path: Ruta de la tabla Delta Lake
            partition_cols: Columnas de partición
            time_range_config: Configuración con:
                - period_column: Columna que define el período
                - period_values: Lista de valores del período a eliminar
                - additional_filters: Filtros adicionales (opcional)
        """
        if not time_range_config:
            raise ValueError("time_range_config es requerido para modo 'time_range'")
        
        period_column = time_range_config.get('period_column')
        period_values = time_range_config.get('period_values')
        additional_filters = time_range_config.get('additional_filters')
        
        if not period_column:
            raise ValueError("period_column es requerido en time_range_config")
        
        self.logger.info("=== MODO TIME_RANGE (Delta Lake): DELETE + APPEND ===")
        self.logger.info(f"Período: {period_column} = {period_values}")
        
        deleted_count = self.delete_manager.delete_period_data(
            delta_table_path=path,
            period_column=period_column,
            period_values=period_values,
            additional_filters=additional_filters
        )
        
        new_count = df.count()
        self.logger.info(f"Iniciando APPEND de {new_count} registros nuevos")
        self.append(df, path, partition_cols=partition_cols)
        self.logger.info(f"✅ TIME_RANGE completado (Delta Lake): {deleted_count} eliminados, {new_count} insertados")
    
    def cleanup(self, path: str) -> None:
        """Elimina datos existentes en la ruta (DROP TABLE en Delta Lake)"""
        try:
            normalized_path = self._normalize_path(path)
            hadoop_conf = self.spark._jsc.hadoopConfiguration()
            uri = self.spark._jvm.java.net.URI(normalized_path)
            fs = self.spark._jvm.org.apache.hadoop.fs.FileSystem.get(uri, hadoop_conf)
            fs_path = self.spark._jvm.org.apache.hadoop.fs.Path(normalized_path)
            
            if fs.exists(fs_path):
                deleted = fs.delete(fs_path, True)
                if deleted:
                    self.logger.info(f"🧹 Ruta Delta Lake limpiada exitosamente: {path}")
                else:
                    self.logger.warning(f"⚠️ No se pudo eliminar completamente la ruta: {path}")
            else:
                self.logger.info(f"ℹ️ Ruta no encontrada (nada que eliminar): {path}")
        except Exception as exc:
            self.logger.error(f"Error eliminando datos existentes en {path}: {exc}")
            raise
    
    def _write(self, df, path: str, mode: str, partition_cols: Optional[List[str]] = None) -> None:
        """Método interno para escribir datos en formato Delta Lake"""
        try:
            writer = df.write.format("delta").mode(mode)
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
            writer.save(path)
            self.logger.info(f"✅ Escritura Delta Lake completada en modo {mode} para {path}")
            self._optimize_table(path)
        except Exception as exc:
            self.logger.error(f"Error al escribir en Delta Lake: {exc}")
            raise
    
    def _optimize_table(self, path: str):
        """Optimiza la tabla Delta Lake usando OPTIMIZE y COMPACTION"""
        try:
            if DeltaTable.isDeltaTable(self.spark, path):
                delta_table = DeltaTable.forPath(self.spark, path)
                delta_table.optimize().executeCompaction()
                self.logger.info(f"Tabla Delta Lake optimizada: {path}")
        except Exception as exc:
            self.logger.warning(f"No se pudo optimizar la tabla Delta Lake: {exc}")
    
    def _normalize_path(self, path: str) -> str:
        """Normaliza la ruta para operaciones del filesystem de Hadoop"""
        if path.startswith("s3://"):
            return "s3a://" + path[5:]
        return path


__all__ = ["DeltaTableWriter"]

