"""
Factory para proveedores de configuración en extract_data.
"""
from __future__ import annotations

import boto3

from aje_libs.datalake.extract_data.services.configuration.csv_configuration_provider import (
    CsvExtractionConfigurationProvider,
)
from aje_libs.datalake.shared.services import LocalCsvLoader, MultiSourceCsvLoader, S3CsvLoader
from aje_libs.datalake.shared.contracts import IConfigurationProvider
from aje_libs.datalake.shared.contracts.logging import ILogger


class ConfigurationProviderFactory:
    """Crea proveedores de configuración según el tipo requerido."""

    @staticmethod
    def create(provider_type: str, logger: ILogger = None, s3_client=None) -> IConfigurationProvider:
        provider_type = (provider_type or "csv").lower()
        s3_client = s3_client or boto3.client("s3")

        if provider_type == "csv":
            local_loader = LocalCsvLoader()
            s3_loader = S3CsvLoader(s3_client)
            csv_loader = MultiSourceCsvLoader(
                loaders={
                    "s3": s3_loader,
                    "file": local_loader,
                },
                default_loader=local_loader,
            )
            return CsvExtractionConfigurationProvider(csv_loader=csv_loader, logger=logger)

        raise ValueError(f"Configuration provider type no soportado: {provider_type}")


__all__ = ["ConfigurationProviderFactory"]

