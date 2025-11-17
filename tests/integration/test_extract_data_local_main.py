from types import SimpleNamespace

import pytest

import extract_data_local


class DummyArgs(SimpleNamespace):
    """Objeto simple que imita argparse.Namespace."""


@pytest.mark.integration
def test_extract_data_local_main_dry_run(monkeypatch):
    """
    Smoke test para extract_data_local.main en modo --dry-run.
    - Evita cargar .env real y evitar llamadas a AWS/BD.
    """

    # 1. Parchear parse_arguments para simular CLI
    def fake_parse_arguments():
        return DummyArgs(
            table="my_table",
            mode="normal",
            log_level="INFO",
            dry_run=True,
        )

    monkeypatch.setattr(extract_data_local, "parse_arguments", fake_parse_arguments)

    # 2. Parchear build_extraction_config_from_env para no depender de .env
    class DummyExtractionConfig:
        def __init__(self):
            self.project_name = "proj"
            self.team = "team"
            self.data_source = "ds"
            self.endpoint_name = "endpoint"
            self.environment = "dev"
            self.table_name = "my_table"
            self.max_threads = 1
            self.chunk_size = 1000
            self.output_format = "parquet"
            self.loader_type = "s3"
            self.formatter_type = "parquet"
            self.raw_storage = None
            self.monitoring = None
            self.notification_targets = {}
            self.notification_target = None
            self.config_sources = {}
            self.load_mode = SimpleNamespace(value="normal")

    monkeypatch.setattr(
        extract_data_local,
        "build_extraction_config_from_env",
        lambda table, mode: DummyExtractionConfig(),
    )

    # 3. Parchear LoggerService para no configurar logging global real
    class DummyLogger:
        def info(self, *_args, **_kwargs):
            pass

        def debug(self, *_args, **_kwargs):
            pass

        def warning(self, *_args, **_kwargs):
            pass

        def error(self, *_args, **_kwargs):
            pass

        def critical(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(
        extract_data_local.LoggerService,
        "configure_global",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        extract_data_local.LoggerService,
        "get_logger",
        lambda *_args, **_kwargs: DummyLogger(),
    )

    # 4. Parchear DataExtractionOrchestrator para que no conecte a nada
    class DummyOrchestrator:
        def __init__(self, *_, **__):
            self.configuration_provider = None
            self.table_config = None

        def _load_configurations(self):
            # Simular carga de configuraciones mínima
            self.table_config = SimpleNamespace(
                source_table="src_table",
                load_type="full",
            )

    monkeypatch.setattr(
        extract_data_local,
        "DataExtractionOrchestrator",
        DummyOrchestrator,
    )

    # 5. Ejecutar main y verificar exit code
    exit_code = extract_data_local.main()
    assert exit_code == 0


