# -*- coding: utf-8 -*-
"""
ParquetTableWriter - Implementación de IDataWriter usando PySpark puro (sin Delta/Iceberg).
Estructura estándar para compatibilidad con otros formatos.
Usa solo PySpark nativo para escribir en formato Parquet.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from aje_libs.datalake.shared.contracts.storage import IDataWriter
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger


class ParquetTableWriter(IDataWriter):
    """
    Implementación de IDataWriter usando PySpark puro (Parquet).
    Proporciona operaciones CRUD para tablas Parquet sin dependencias de Delta Lake o Iceberg.
    
    Nota: Las operaciones de merge y time_range se implementan manualmente ya que
    Parquet no tiene soporte nativo de MERGE como Delta/Iceberg.
    """
    
    def __init__(self, spark, logger=None):
        """
        Inicializa el writer de Parquet
        
        Args:
            spark: SparkSession
            logger: Logger (opcional)
        """
        self.spark = spark
        self.logger = logger or DataLakeLogger.get_logger(__name__)
    
    def overwrite(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Sobrescribe datos en la tabla Parquet"""
        self._write(df, path, mode="overwrite", partition_cols=partition_cols)
    
    def append(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Inserta datos en modo append a la tabla Parquet"""
        self._write(df, path, mode="append", partition_cols=partition_cols)
    
    def merge(self, df, path: str, merge_condition: str, partition_cols: Optional[List[str]] = None) -> None:
        """
        Realiza operaciones de merge/upsert usando PySpark puro.
        
        Como Parquet no tiene soporte nativo de MERGE, se implementa manualmente:
        1. Lee los datos existentes
        2. Hace un full outer join con los nuevos datos
        3. Aplica la lógica de merge según la condición
        4. Escribe el resultado completo (OVERWRITE)
        
        Args:
            df: DataFrame con los datos a mergear
            path: Ruta de la tabla Parquet
            merge_condition: Condición SQL para el merge (ej: "old.id = new.id")
            partition_cols: Columnas de partición
        """
        try:
            self.logger.info(f"🔄 Iniciando merge en Parquet (implementación manual): {path}")
            
            # Verificar si la tabla existe
            existing_df = None
            try:
                existing_df = self.spark.read.format("parquet").load(path)
                existing_count = existing_df.count()
                self.logger.info(f"📊 Datos existentes: {existing_count} registros")
            except Exception:
                self.logger.info("ℹ️ Tabla no existe aún, creando nueva")
                # Si no existe, simplemente escribir los nuevos datos
                self.overwrite(df, path, partition_cols=partition_cols)
                return
            
            # Parsear la condición de merge (ej: "old.id = new.id")
            # Extraer las columnas de la condición
            condition_parts = merge_condition.replace("old.", "").replace("new.", "").split("=")
            if len(condition_parts) != 2:
                raise ValueError(f"Condición de merge inválida: {merge_condition}. Debe ser formato 'old.col = new.col'")
            
            join_col = condition_parts[0].strip()
            
            # Renombrar columnas para evitar conflictos
            existing_df_renamed = existing_df.alias("old")
            new_df_renamed = df.alias("new")
            
            # Hacer full outer join
            merged_df = existing_df_renamed.join(
                new_df_renamed,
                existing_df_renamed[join_col] == new_df_renamed[join_col],
                how="full_outer"
            )
            
            # Seleccionar columnas: preferir 'new' sobre 'old' cuando existen ambas
            # Esto implementa la lógica de UPDATE cuando hay match, INSERT cuando no
            from pyspark.sql.functions import col, when
            
            select_exprs = []
            for col_name in df.columns:
                new_col = col(f"new.{col_name}")
                old_col = col(f"old.{col_name}")
                # Si existe en new, usar new; si no, usar old
                select_exprs.append(
                    when(new_col.isNotNull(), new_col).otherwise(old_col).alias(col_name)
                )
            
            merged_df = merged_df.select(*select_exprs)
            
            # Filtrar filas donde al menos una columna no es null (evitar filas completamente null)
            # Usar la primera columna como referencia para verificar si la fila tiene datos
            first_col = df.columns[0]
            merged_df = merged_df.filter(col(first_col).isNotNull())
            
            merged_count = merged_df.count()
            self.logger.info(f"📊 Datos después de merge: {merged_count} registros")
            
            # Escribir resultado (OVERWRITE porque ya incluimos todo)
            self.overwrite(merged_df, path, partition_cols=partition_cols)
            self.logger.info(f"✅ Merge completado en {path}")
            
        except Exception as exc:
            self.logger.error(f"❌ Error en merge Parquet: {exc}")
            raise
    
    def write_time_range(
        self,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        time_range_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Operación específica para eliminar por rango y volver a escribir en Parquet.
        
        Como Parquet no tiene soporte nativo de DELETE, se implementa manualmente:
        1. Lee los datos existentes
        2. Filtra eliminando los registros del período especificado
        3. Agrega los nuevos datos
        4. Escribe el resultado completo (OVERWRITE)
        
        Args:
            df: DataFrame con los nuevos datos
            path: Ruta de la tabla Parquet
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
        
        self.logger.info("=== MODO TIME_RANGE (Parquet): DELETE + APPEND (implementación manual) ===")
        self.logger.info(f"Período: {period_column} = {period_values}")
        
        try:
            # Leer datos existentes
            existing_df = None
            deleted_count = 0
            try:
                existing_df = self.spark.read.format("parquet").load(path)
                count_before = existing_df.count()
                
                # Construir condición de filtro para eliminar el período
                from pyspark.sql.functions import col
                
                # Filtrar por período
                if isinstance(period_values, list):
                    filter_condition = ~col(period_column).isin(period_values)
                else:
                    filter_condition = col(period_column) != period_values
                
                # Aplicar filtros adicionales si existen
                if additional_filters:
                    for filter_col, filter_value in additional_filters.items():
                        if isinstance(filter_value, list):
                            filter_condition = filter_condition & col(filter_col).isin(filter_value)
                        else:
                            filter_condition = filter_condition & (col(filter_col) == filter_value)
                
                # Filtrar datos existentes (eliminar el período)
                existing_df = existing_df.filter(filter_condition)
                count_after = existing_df.count()
                deleted_count = count_before - count_after
                
                self.logger.info(f"🗑️ Eliminados {deleted_count} registros del período {period_values}")
                
            except Exception as e:
                self.logger.info(f"ℹ️ Tabla no existe aún o error leyendo: {e}. Creando nueva.")
                existing_df = None
            
            # Combinar datos existentes (filtrados) con nuevos datos
            if existing_df is not None and existing_df.count() > 0:
                combined_df = existing_df.unionByName(df, allowMissingColumns=True)
            else:
                combined_df = df
            
            new_count = df.count()
            final_count = combined_df.count()
            
            self.logger.info(f"📊 Datos finales: {final_count} registros ({deleted_count} eliminados, {new_count} nuevos)")
            
            # Escribir resultado completo (OVERWRITE)
            self.overwrite(combined_df, path, partition_cols=partition_cols)
            self.logger.info(f"✅ TIME_RANGE completado (Parquet): {deleted_count} eliminados, {new_count} insertados")
            
        except Exception as exc:
            self.logger.error(f"❌ Error en write_time_range Parquet: {exc}")
            raise
    
    def cleanup(self, path: str) -> None:
        """Elimina datos existentes en la ruta (elimina directorio Parquet)"""
        try:
            normalized_path = self._normalize_path(path)
            hadoop_conf = self.spark._jsc.hadoopConfiguration()
            uri = self.spark._jvm.java.net.URI(normalized_path)
            fs = self.spark._jvm.org.apache.hadoop.fs.FileSystem.get(uri, hadoop_conf)
            fs_path = self.spark._jvm.org.apache.hadoop.fs.Path(normalized_path)
            
            if fs.exists(fs_path):
                deleted = fs.delete(fs_path, True)  # True = recursive
                if deleted:
                    self.logger.info(f"🧹 Ruta Parquet limpiada exitosamente: {path}")
                else:
                    self.logger.warning(f"⚠️ No se pudo eliminar completamente la ruta: {path}")
            else:
                self.logger.info(f"ℹ️ Ruta no encontrada (nada que eliminar): {path}")
        except Exception as exc:
            self.logger.error(f"Error eliminando datos existentes en {path}: {exc}")
            raise
    
    def _write(self, df, path: str, mode: str, partition_cols: Optional[List[str]] = None) -> None:
        """Método interno para escribir datos en formato Parquet usando PySpark puro"""
        try:
            writer = df.write.format("parquet").mode(mode)
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
            writer.save(path)
            self.logger.info(f"✅ Escritura Parquet completada en modo {mode} para {path}")
        except Exception as exc:
            self.logger.error(f"Error al escribir en Parquet: {exc}")
            raise
    
    def _normalize_path(self, path: str) -> str:
        """Normaliza la ruta para operaciones del filesystem de Hadoop"""
        if path.startswith("s3://"):
            return "s3a://" + path[5:]
        return path


__all__ = ["ParquetTableWriter"]

