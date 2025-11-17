from typing import Any, Dict, List

import pytest

# Saltar este módulo si no hay pyspark (light_transform usa pyspark internamente)
pytest.importorskip("pyspark", reason="pyspark requerido para tests de LightTransformOrchestrator")

from aje_libs.datalake.light_transform.models import LightTransformConfig
from aje_libs.datalake.light_transform.orchestrators.light_transform_orchestrator import (
    LightTransformOrchestrator,
)
from aje_libs.datalake.shared.models import LoadMode, ResourceRef


class FakeMonitor:
    def __init__(self) -> None:
        self.start_calls: List[Dict[str, Any]] = []
        self.success_calls: List[Dict[str, Any]] = []

    def log_start(self, table_name: str, job_name: str, metadata: Dict[str, Any]) -> str:
        self.start_calls.append(
            {"table_name": table_name, "job_name": job_name, "metadata": metadata}
        )
        return "process-id-1"

    def log_success(self, table_name: str, job_name: str, metadata: Dict[str, Any]) -> None:
        self.success_calls.append(
            {"table_name": table_name, "job_name": job_name, "metadata": metadata}
        )


class FakeProcessor:
    def __init__(self) -> None:
        self.called_with_config: List[LightTransformConfig] = []

    def process_table(self, config: LightTransformConfig) -> None:
        self.called_with_config.append(config)


class FakeComponentFactory:
    """Factory mínima para no depender de implementación real."""

    def __init__(self, monitor: FakeMonitor, processor: FakeProcessor) -> None:
        self._monitor = monitor
        self._processor = processor

    def create_monitor(self, config: LightTransformConfig, process_guid: str):
        return self._monitor

    def create_processor(self, config: LightTransformConfig, spark: Any, s3_client: Any):
        return self._processor


def build_minimal_light_transform_config() -> LightTransformConfig:
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
        source_storage=ResourceRef(provider="s3", location="s3://raw-bucket"),
        stage_storage=ResourceRef(provider="s3", location="s3://stage-bucket"),
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
def test_light_transform_orchestrator_run_with_config_happy_path(monkeypatch):
    """
    Smoke test liviano de run_with_config:
    - Inicializa logging, Spark, monitor y processor vía factory fake.
    - Ejecuta processor.process_table(config).
    - Llama a log_start y log_success.
    """
    cfg = build_minimal_light_transform_config()
    fake_monitor = FakeMonitor()
    fake_processor = FakeProcessor()
    fake_factory = FakeComponentFactory(fake_monitor, fake_processor)

    orchestrator = LightTransformOrchestrator(component_factory=fake_factory)

    # Evitar crear Spark real ni boto3 real
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

    orchestrator.run_with_config(cfg, log_level="INFO")

    # Verificar que el processor fue invocado
    assert fake_processor.called_with_config == [cfg]

    # Verificar que el monitor registró inicio y éxito
    assert len(fake_monitor.start_calls) == 1
    assert len(fake_monitor.success_calls) == 1
    assert fake_monitor.start_calls[0]["table_name"] == "tbl"
    assert fake_monitor.success_calls[0]["table_name"] == "tbl"


