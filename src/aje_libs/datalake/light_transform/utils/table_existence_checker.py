# -*- coding: utf-8 -*-
"""
TableExistenceChecker - Utilidad para verificar existencia de tablas de forma agnóstica al formato
Aplica Strategy Pattern para soportar múltiples formatos (Delta, Iceberg, etc.)
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

from ...shared.services.logging import LoggerService


class TableExistenceChecker:
    """
    Verifica si una tabla existe de forma agnóstica al formato.
    Soporta Delta Lake, Apache Iceberg y otros formatos.
    """
    
    @staticmethod
    def table_exists(spark: "SparkSession", path: str, table_format: str = "delta") -> bool:
        """
        Verifica si una tabla existe según el formato especificado
        
        Args:
            spark: SparkSession
            path: Ruta o nombre de la tabla
            table_format: Formato de tabla ('delta', 'iceberg', etc.)
            
        Returns:
            True si la tabla existe, False en caso contrario
        """
        table_format_lower = table_format.lower()
        
        try:
            if table_format_lower == 'delta':
                return TableExistenceChecker._delta_table_exists(spark, path)
            elif table_format_lower == 'iceberg':
                return TableExistenceChecker._iceberg_table_exists(spark, path)
            elif table_format_lower in ('parquet', 'spark'):
                # Parquet/PySpark puro usa verificación genérica
                return TableExistenceChecker._parquet_table_exists(spark, path)
            else:
                # Para otros formatos, intentar verificación genérica
                logger = LoggerService.get_logger(__name__)
                logger.warning(f"Formato '{table_format}' no tiene verificación específica. Intentando genérica...")
                return TableExistenceChecker._generic_table_exists(spark, path)
        except Exception as e:
            logger = LoggerService.get_logger(__name__)
            logger.debug(f"Error verificando existencia de tabla '{path}': {e}")
            return False
    
    @staticmethod
    def _delta_table_exists(spark: "SparkSession", path: str) -> bool:
        """Verifica si una tabla Delta Lake existe"""
        try:
            from delta.tables import DeltaTable
            return DeltaTable.isDeltaTable(spark, path)
        except ImportError:
            logger = LoggerService.get_logger(__name__)
            logger.warning("Delta Lake no está disponible. No se puede verificar existencia de tabla Delta.")
            return False
        except Exception:
            return False
    
    @staticmethod
    def _iceberg_table_exists(spark: "SparkSession", path: str) -> bool:
        """Verifica si una tabla Iceberg existe"""
        try:
            # Parsear nombre de tabla
            table_name = TableExistenceChecker._parse_iceberg_table_name(path)
            
            # Intentar queryar la tabla
            spark.sql(f"SELECT 1 FROM {table_name} LIMIT 1")
            return True
        except Exception:
            return False
    
    @staticmethod
    def _parquet_table_exists(spark: "SparkSession", path: str) -> bool:
        """Verifica si una tabla Parquet existe"""
        try:
            # Intentar leer la ruta como DataFrame Parquet
            spark.read.format("parquet").load(path).limit(1).collect()
            return True
        except Exception:
            return False
    
    @staticmethod
    def _generic_table_exists(spark: "SparkSession", path: str) -> bool:
        """Verificación genérica de existencia de tabla"""
        try:
            # Intentar leer la ruta como DataFrame
            spark.read.format("parquet").load(path).limit(1).collect()
            return True
        except Exception:
            return False
    
    @staticmethod
    def _parse_iceberg_table_name(path: str) -> str:
        """Parsea la ruta a un nombre de tabla válido para Iceberg"""
        # Si es formato catalog.database.table, retornarlo directamente
        if "." in path and not path.startswith("s3://") and not path.startswith("/"):
            return path
        
        # Si es path (s3://bucket/path), convertir a formato de tabla
        return path.replace("s3://", "").replace("/", "_")


__all__ = ['TableExistenceChecker']

