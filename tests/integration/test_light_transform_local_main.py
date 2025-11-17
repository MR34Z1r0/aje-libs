from types import SimpleNamespace

import pytest

# Si no hay pyspark instalado, saltar todo este módulo (light_transform depende de pyspark)
pytest.importorskip("pyspark", reason="pyspark requerido para tests de light_transform local")

import light_transform_local


class DummyArgs(SimpleNamespace):
    """Objeto simple que imita argparse.Namespace."""


@pytest.mark.integration
def test_light_transform_local_main_happy_path(monkeypatch):
    """
    Smoke test para light_transform_local.main:
    - Usa configuración mínima.
    - Evita tocar Spark real y AWS.
    """

    # 1. Parchear parse_arguments para simular CLI
    def fake_parse_arguments():
        return DummyArgs(
            table="my_table",
            mode="normal",
            config_profile="local_csv",
            job_name="job",
            date_process=None,
            monitor=None,
            config_source=None,
            loader=None,
            writer=None,
            project="proj",
            team="team",
            data_source="ds",
            endpoint="endpoint",
            environment="dev",
            raw_bucket="raw-bucket",
            stage_bucket="stage-bucket",
            logs_table=None,
            watermarks_table=None,
            source_provider=None,
            stage_provider=None,
            log_provider=None,
            watermark_provider=None,
            topic_arn=None,
            arn_topic_failed=None,
            arn_topic_success=None,
            arn_topic_warning=None,
            notification_provider="sns",
            tables="tables.csv",
            credentials="creds.csv",
            columns="cols.csv",
            tables_provider=None,
            credentials_provider=None,
            columns_provider=None,
            log_level="INFO",
            set=[],
        )

    monkeypatch.setattr(
        light_transform_local,
        "parse_arguments",
        fake_parse_arguments,
    )

    # 2. Parchear build_config_dictionary para que devuelva un diccionario mínimo
    def fake_build_config_dictionary(_args):
        return {
            "overrides": {
                "job_name": "job",
                "table_name": "my_table",
                "project_name": "proj",
                "team": "team",
                "data_source": "ds",
                "endpoint_name": "endpoint",
                "environment": "dev",
                "load_mode": "normal",
                "source_storage": {
                    "provider": "s3",
                    "location": "raw-bucket",
                },
                "stage_storage": {
                    "provider": "s3",
                    "location": "stage-bucket",
                },
                "config_sources": {
                    "tables": {
                        "provider": "csv",
                        "location": "tables.csv",
                    }
                },
            }
        }

    monkeypatch.setattr(
        light_transform_local,
        "build_config_dictionary",
        fake_build_config_dictionary,
    )

    # 3. Parchear LoggerService para evitar logging real
    class DummyLogger:
        def info(self, *_args, **_kwargs):
            pass

        def debug(self, *_args, **_kwargs):
            pass

        def warning(self, *_args, **_kwargs):
            pass

        def error(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(
        light_transform_local.LoggerService,
        "configure_global",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        light_transform_local.LoggerService,
        "get_logger",
        lambda *_args, **_kwargs: DummyLogger(),
    )
    monkeypatch.setattr(
        light_transform_local.LoggerService,
        "print_environment_info",
        lambda *args, **kwargs: None,
    )

    # 4. Parchear LightTransformOrchestrator.run_with_config para no ejecutar lógica real
    class DummyOrchestrator:
        def __init__(self, *_, **__):
            self.last_status = "success"
            self.last_error_type = None
            self.last_error_message = None

        def run_with_config(self, *_args, **_kwargs):
            # No hace nada, solo simula ejecución exitosa
            self.last_status = "success"

    monkeypatch.setattr(
        light_transform_local,
        "LightTransformOrchestrator",
        DummyOrchestrator,
    )

    # 5. Ejecutar main y verificar exit code
    exit_code = light_transform_local.main()
    assert exit_code == 0


