from typing import Any

import pytest

# Saltar este módulo si no hay pyspark disponible
pytest.importorskip("pyspark", reason="pyspark requerido para tests de LightTransformOrchestrator")

from aje_libs.datalake.light_transform.models import LightTransformConfig
from aje_libs.datalake.light_transform.orchestrators.light_transform_orchestrator import (
    LightTransformOrchestrator,
)
from aje_libs.datalake.shared.models import LoadMode, ResourceRef
from aje_libs.datalake.shared.exceptions import TransformationException, DataValidationError


class DummyProcessor:
    def __init__(self, exc: Exception):
        self.exc = exc

    def process_table(self, *_args, **_kwargs):
        raise self.exc


class DummyComponentFactory:
    def __init__(self, processor: DummyProcessor):
        self._processor = processor

    def create_monitor(self, config: LightTransformConfig, process_guid: str):
        return None  # Para estos tests no necesitamos monitor real

    def create_processor(self, config: LightTransformConfig, spark: Any, s3_client: Any):
        return self._processor


def build_minimal_lt_config() -> LightTransformConfig:
    return LightTransformConfig(
        job_name="job",
        table_name="tbl",
        load_mode=LoadMode.NORMAL,
        date_process=None,
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        source_storage=ResourceRef(provider="s3", location="raw-bucket"),
        stage_storage=ResourceRef(provider="s3", location="stage-bucket"),
        log_storage=None,
        watermark_storage=None,
        config_sources={
            "tables": ResourceRef(provider="csv", location="tables.csv"),
        },
        notification_target=None,
        notification_targets={},
        monitor_type="dynamodb",
        config_source_type="csv",
        data_loader_type="spark",
        data_writer_type="delta",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc_cls,error_type",
    [
        (TransformationException, "TransformationException"),
        (DataValidationError, "DataValidationException"),
    ],
)
def test_light_transform_orchestrator_run_with_config_sets_error_status(monkeypatch, exc_cls, error_type):
    """
    Fuerza excepciones específicas en processor.process_table y valida que:
    - Se actualicen last_status y last_error_type correctamente.
    - No se propague la excepción hacia afuera.
    """
    cfg = build_minimal_lt_config()
    processor = DummyProcessor(exc=exc_cls("boom"))
    factory = DummyComponentFactory(processor)

    orchestrator = LightTransformOrchestrator(component_factory=factory)

    # Evitar Spark y boto3 reales
    class DummySpark:
        class DummyContext:
            applicationId = "spark-app-id"

            class DummyJsc:
                class DummyHadoopConf:
                    def set(self, *_args, **_kwargs):
                        pass

                def hadoopConfiguration(self):
                    return self.DummyHadoopConf()

            _jsc = DummyJsc()

        sparkContext = DummyContext()

        def stop(self):
            pass

    def fake_initialize_spark(self, table_format: str = "delta"):  # type: ignore[override]
        self.spark = DummySpark()

    monkeypatch.setattr(
        "aje_libs.datalake.light_transform.orchestrators.light_transform_orchestrator.SparkConfigBuilder.configure_for_format",  # noqa: E501
        lambda spark_builder, table_format, logger: DummySpark(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        LightTransformOrchestrator,
        "initialize_spark",
        fake_initialize_spark,
    )
    monkeypatch.setattr(
        "aje_libs.datalake.light_transform.orchestrators.light_transform_orchestrator.boto3.client",  # noqa: E501
        lambda *_args, **_kwargs: object(),
    )

    # Ejecutar: las excepciones se manejan internamente
    orchestrator.run_with_config(cfg, log_level="INFO")

    assert orchestrator.last_status in ("error", "warning")
    assert orchestrator.last_error_type in (error_type, "Warning")


