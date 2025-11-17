# -*- coding: utf-8 -*-
"""
IcebergTableWriter - Implementación de IDataWriter para Apache Iceberg.
Estructura estándar para compatibilidad con otros formatos (Delta Lake, etc.)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from aje_libs.datalake.shared.contracts.storage import IDataWriter
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger
from .iceberg_table_manager import TimeRangeDeleteManager


class IcebergTableWriter(IDataWriter):
    """
    Implementación de IDataWriter basada en Apache Iceberg.
    Proporciona operaciones CRUD para tablas Apache Iceberg.
    """
    
    def __init__(self, spark, logger=None, catalog: Optional[str] = None):
        """
        Inicializa el writer de Iceberg
        
        Args:
            spark: SparkSession
            logger: Logger (opcional)
            catalog: Nombre del catálogo de Iceberg (opcional, por defecto usa spark_catalog)
        """
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.catalog = catalog or "spark_catalog"
        self.delete_manager = TimeRangeDeleteManager(spark, self.logger)
        
        # Configurar extensiones de Iceberg si no están configuradas
        self._ensure_iceberg_config()
    
    def overwrite(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Sobrescribe datos en la tabla Iceberg"""
        self._write(df, path, mode="overwrite", partition_cols=partition_cols)
    
    def append(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Inserta datos en modo append a la tabla Iceberg"""
        self._write(df, path, mode="append", partition_cols=partition_cols)
    
    def merge(self, df, path: str, merge_condition: str, partition_cols: Optional[List[str]] = None) -> None:
        """
        Realiza operaciones de merge/upsert usando MERGE INTO de Iceberg
        
        Args:
            df: DataFrame con los datos a mergear
            path: Ruta de la tabla Iceberg (formato: catalog.database.table o path completo)
            merge_condition: Condición SQL para el merge (ej: "target.id = source.id")
            partition_cols: Columnas de partición (ignoradas en merge, Iceberg las gestiona)
        """
        try:
            # Iceberg usa MERGE INTO SQL similar a Delta
            table_name = self._parse_table_name(path)
            
            # Crear vista temporal para los datos nuevos
            temp_view = "temp_merge_source"
            df.createOrReplaceTempView(temp_view)
            
            # Construir query MERGE INTO
            # Nota: Esto requiere que la tabla ya exista en Iceberg
            merge_sql = f"""
                MERGE INTO {table_name} AS target
                USING {temp_view} AS source
                ON {merge_condition}
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """
            
            self.spark.sql(merge_sql)
            self.logger.info(f"✅ Merge completado en {path}")
            
            # Limpiar vista temporal
            self.spark.catalog.dropTempView(temp_view)
            
        except Exception as exc:
            self.logger.error(f"❌ Error en merge Iceberg: {exc}")
            raise
    
    def write_time_range(
        self,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        time_range_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Operación específica para eliminar por rango y volver a escribir en Iceberg
        
        Args:
            df: DataFrame con los nuevos datos
            path: Ruta de la tabla Iceberg
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
        
        self.logger.info("=== MODO TIME_RANGE (Iceberg): DELETE + APPEND ===")
        self.logger.info(f"Período: {period_column} = {period_values}")
        
        deleted_count = self.delete_manager.delete_period_data(
            iceberg_table_path=path,
            period_column=period_column,
            period_values=period_values,
            additional_filters=additional_filters
        )
        
        new_count = df.count()
        self.logger.info(f"Iniciando APPEND de {new_count} registros nuevos")
        self.append(df, path, partition_cols=partition_cols)
        self.logger.info(f"✅ TIME_RANGE completado (Iceberg): {deleted_count} eliminados, {new_count} insertados")
    
    def cleanup(self, path: str) -> None:
        """Elimina datos existentes en la ruta (DROP TABLE en Iceberg)"""
        try:
            table_name = self._parse_table_name(path)
            
            if self._table_exists(path):
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                self.spark.sql(drop_sql)
                self.logger.info(f"🧹 Tabla Iceberg eliminada: {path}")
            else:
                self.logger.info(f"ℹ️ Tabla no encontrada (nada que eliminar): {path}")
                
        except Exception as exc:
            self.logger.error(f"Error eliminando tabla Iceberg en {path}: {exc}")
            raise
    
    def _write(self, df, path: str, mode: str, partition_cols: Optional[List[str]] = None) -> None:
        """Método interno para escribir datos en formato Iceberg"""
        try:
            writer = df.write.format("iceberg").mode(mode)
            
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
            
            # Iceberg puede usar saveAsTable o save
            if self._is_catalog_path(path):
                # Formato catalog.database.table
                table_name = self._parse_table_name(path)
                writer.saveAsTable(table_name)
            else:
                # Formato path (s3://bucket/path)
                writer.save(path)
            
            self.logger.info(f"✅ Escritura Iceberg completada en modo {mode} para {path}")
            self._optimize_table(path)
            
        except Exception as exc:
            self.logger.error(f"Error al escribir en Iceberg: {exc}")
            raise
    
    def _optimize_table(self, path: str):
        """Optimiza la tabla Iceberg usando OPTIMIZE y VACUUM"""
        try:
            if not self._table_exists(path):
                return
            
            table_name = self._parse_table_name(path)
            
            # Optimizar archivos pequeños
            optimize_sql = f"OPTIMIZE {table_name}"
            self.spark.sql(optimize_sql)
            self.logger.info(f"Tabla Iceberg optimizada: {path}")
            
            # Opcional: VACUUM para eliminar archivos antiguos
            # vacuum_sql = f"VACUUM {table_name}"
            # self.spark.sql(vacuum_sql)
            
        except Exception as exc:
            self.logger.warning(f"No se pudo optimizar la tabla Iceberg: {exc}")
    
    def _parse_table_name(self, path: str) -> str:
        """Parsea la ruta a un nombre de tabla válido para Iceberg"""
        # Si es formato catalog.database.table, retornarlo directamente
        if self._is_catalog_path(path):
            return path
        
        # Si es path (s3://bucket/path), convertir a formato de tabla
        # Esto requiere configuración adicional del catálogo
        # Por ahora, asumimos que se pasa directamente el nombre de tabla
        return path.replace("s3://", "").replace("/", "_")
    
    def _is_catalog_path(self, path: str) -> bool:
        """Verifica si el path es formato de catálogo (catalog.database.table)"""
        return "." in path and not path.startswith("s3://") and not path.startswith("/")
    
    def _table_exists(self, path: str) -> bool:
        """Verifica si la tabla Iceberg existe"""
        try:
            table_name = self._parse_table_name(path)
            self.spark.sql(f"SELECT 1 FROM {table_name} LIMIT 1")
            return True
        except Exception:
            return False
    
    def _ensure_iceberg_config(self):
        """Asegura que Spark tenga las configuraciones necesarias para Iceberg"""
        # Estas configuraciones deberían estar en SparkSession, pero las verificamos aquí
        # Si ya están configuradas, no las sobrescribimos
        conf = self.spark.sparkContext.getConf()
        
        if conf.get("spark.sql.extensions", None) != "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions":
            self.logger.warning(
                "⚠️ Spark no tiene configuradas las extensiones de Iceberg. "
                "Asegúrate de configurar 'spark.sql.extensions' y 'spark.sql.catalog.spark_catalog' "
                "al crear el SparkSession."
            )


__all__ = ["IcebergTableWriter"]

