"""
Factory para construir el procesador de Light Transform.
"""
from __future__ import annotations

import boto3

from aje_libs.datalake.light_transform.contracts.data_processing import ILightTransformProcessor
from aje_libs.datalake.light_transform.services.configuration.configuration_service import ConfigurationService
from aje_libs.datalake.light_transform.services.data_processing import DataProcessor, SparkDataLoader
from aje_libs.datalake.light_transform.services.storage.delta_table_manager import DeltaTableManager, DeltaTableWriter
from aje_libs.datalake.light_transform.services.transformation.transformation_engine import TransformationEngine
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger
from aje_libs.datalake.shared.services import LocalCsvLoader, MultiSourceCsvLoader, S3CsvLoader


class LightTransformProcessorFactory:
    """Factory responsable de ensamblar las dependencias del `DataProcessor`."""

    def __init__(
        self,
        spark,
        s3_client=None,
        logger=None,
        config_source_type: str = "csv",
        data_loader_type: str = "spark",
        data_writer_type: str = "delta",
    ):
        self.spark = spark
        self.s3_client = s3_client or boto3.client('s3')
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.config_source_type = config_source_type
        self.data_loader_type = data_loader_type
        self.data_writer_type = data_writer_type

    def _create_configuration_provider(self):
        if self.config_source_type == 'csv':
            local_loader = LocalCsvLoader()
            s3_loader = S3CsvLoader(self.s3_client)
            csv_loader = MultiSourceCsvLoader(
                loaders={
                    's3': s3_loader,
                    'file': local_loader,
                },
                default_loader=local_loader,
            )
            return ConfigurationService(csv_loader=csv_loader, logger=self.logger)
        raise ValueError(f"Config source type no soportado: {self.config_source_type}")

    def _create_data_loader(self):
        if self.data_loader_type == 'spark':
            return SparkDataLoader(self.spark, logger=self.logger, s3_client=self.s3_client)
        raise ValueError(f"Data loader type no soportado: {self.data_loader_type}")

    def _create_data_writer(self):
        if self.data_writer_type == 'delta':
            return DeltaTableWriter(self.spark, logger=self.logger)
        raise ValueError(f"Data writer type no soportado: {self.data_writer_type}")

    def create(self) -> ILightTransformProcessor:
        """Construye una instancia de `ILightTransformProcessor`."""
        configuration_provider = self._create_configuration_provider()
        transformation_engine = TransformationEngine(self.spark)
        data_loader = self._create_data_loader()
        data_writer = self._create_data_writer()

        return DataProcessor(
            spark=self.spark,
            configuration_provider=configuration_provider,
            transformation_engine=transformation_engine,
            data_loader=data_loader,
            data_writer=data_writer,
            logger=self.logger,
        )


__all__ = ["LightTransformProcessorFactory"]

