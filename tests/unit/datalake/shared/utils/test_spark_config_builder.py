import pytest

from aje_libs.datalake.shared.utils.spark_config_builder import SparkConfigBuilder


class DummyBuilder:
    def __init__(self) -> None:
        self.configs = {}

    def config(self, key: str, value: str):
        self.configs[key] = value
        return self


class DummyLogger:
    def __init__(self) -> None:
        self.debug_messages = []

    def debug(self, msg: str, *args, **kwargs):
        self.debug_messages.append(msg)


@pytest.mark.unit
def test_spark_config_builder_configure_for_delta(monkeypatch):
    dummy_builder = DummyBuilder()
    dummy_logger = DummyLogger()

    # Forzar PYSPARK_AVAILABLE=True para evitar ImportError
    monkeypatch.setattr(
        "aje_libs.datalake.shared.utils.spark_config_builder.PYSPARK_AVAILABLE",
        True,
    )

    builder = SparkConfigBuilder.configure_for_format(
        spark_builder=dummy_builder,
        table_format="delta",
        logger=dummy_logger,
    )

    assert builder is dummy_builder
    # Verificar algunas configs clave
    assert builder.configs["spark.sql.extensions"] == "io.delta.sql.DeltaSparkSessionExtension"
    assert builder.configs["spark.sql.catalog.spark_catalog"] == "org.apache.spark.sql.delta.catalog.DeltaCatalog"


@pytest.mark.unit
def test_spark_config_builder_configure_for_iceberg_with_warehouse(monkeypatch):
    dummy_builder = DummyBuilder()
    dummy_logger = DummyLogger()

    monkeypatch.setattr(
        "aje_libs.datalake.shared.utils.spark_config_builder.PYSPARK_AVAILABLE",
        True,
    )

    builder = SparkConfigBuilder.configure_for_format(
        spark_builder=dummy_builder,
        table_format="iceberg",
        logger=dummy_logger,
        warehouse_path="s3://warehouse",
    )

    assert builder is dummy_builder
    assert builder.configs["spark.sql.extensions"].startswith("org.apache.iceberg.spark.extensions.")
    assert "spark.sql.catalog.spark_catalog.warehouse" in builder.configs
    assert builder.configs["spark.sql.catalog.spark_catalog.warehouse"] == "s3://warehouse"


@pytest.mark.unit
def test_spark_config_builder_register_and_get_format_config(monkeypatch):
    dummy_logger = DummyLogger()

    # Evitar llamadas reales a LoggerService
    monkeypatch.setattr(
        "aje_libs.datalake.shared.utils.spark_config_builder.LoggerService.get_logger",
        lambda *_args, **_kwargs: dummy_logger,
    )

    SparkConfigBuilder.register_format_config(
        "custom",
        {"extensions": "ext", "catalog": "cat"},
    )

    cfg = SparkConfigBuilder.get_format_config("custom")

    assert cfg["extensions"] == "ext"
    assert cfg["catalog"] == "cat"


