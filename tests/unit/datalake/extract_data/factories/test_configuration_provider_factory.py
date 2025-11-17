import boto3
import pytest

from aje_libs.datalake.extract_data.factories.configuration_provider_factory import (
    ConfigurationProviderFactory,
)


@pytest.mark.unit
def test_configuration_provider_factory_creates_csv_provider(monkeypatch):
    # Evitar que boto3 intente credenciales reales
    class DummyS3Client:
        def __init__(self):
            self.called = True

    monkeypatch.setattr(
        "aje_libs.datalake.extract_data.factories.configuration_provider_factory.boto3.client",
        lambda *_args, **_kwargs: DummyS3Client(),
    )

    provider = ConfigurationProviderFactory.create("csv", logger=None)

    # No validamos implementación interna, solo que se cree algo y no dispare error
    from aje_libs.datalake.extract_data.services.configuration.csv_configuration_provider import (  # noqa: E501
        CsvExtractionConfigurationProvider,
    )

    assert isinstance(provider, CsvExtractionConfigurationProvider)


@pytest.mark.unit
def test_configuration_provider_factory_raises_on_unsupported_type():
    with pytest.raises(ValueError):
        ConfigurationProviderFactory.create("unknown", logger=None)


