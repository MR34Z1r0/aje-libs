"""
Cargadores de datos para Light Transform.
"""
from __future__ import annotations

import os
from typing import Optional

from pyspark.sql import SparkSession

from aje_libs.datalake.shared.contracts.data_access import IDataLoader
from aje_libs.datalake.shared.exceptions import DataValidationError as DataValidationException, ProcessingError
from aje_libs.datalake.shared.contracts.logging import ILogger


class SparkDataLoader(IDataLoader):
    """Carga datos usando Spark desde diferentes orígenes (S3, local, etc.)."""

    def __init__(self, spark: SparkSession, logger: Optional[ILogger] = None, s3_client=None):
        self.spark = spark
        self.logger = logger
        self.s3_client = s3_client

    def exists(self, path: str) -> bool:
        if path.startswith("s3://"):
            if not self.s3_client:
                raise DataValidationException("Se requiere un cliente S3 para validar rutas s3://")
            stripped = path[5:]
            bucket, *rest = stripped.split("/", 1)
            prefix = rest[0] if rest else ""
            try:
                response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
                return response.get("KeyCount", 0) > 0
            except Exception as exc:
                if self.logger:
                    self.logger.error(f"Error verificando ruta S3 {path}: {exc}")
                return False

        local_path = path
        if local_path.startswith("file://"):
            local_path = local_path[7:]
        return os.path.exists(local_path)

    def load(self, path: str):
        try:
            df = self.spark.read.format("parquet").load(path.rstrip("/"))
            df.cache()
            count = df.count()
            if count == 0:
                raise DataValidationException(f"No data to process for path: {path}")
            if self.logger:
                self.logger.info(f"📊 Datos leídos exitosamente: {count} registros desde {path}")
            return df
        except DataValidationException:
            raise
        except DataValidationException:
            raise
        except Exception as exc:
            if self.logger:
                self.logger.error(f"❌ Error leyendo datos desde {path}: {exc}", exc_info=True)
            raise ProcessingError(f"Error leyendo datos desde {path}: {exc}") from exc


__all__ = ["SparkDataLoader"]

