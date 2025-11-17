from typing import Any, Dict, List

import pytest

from aje_libs.datalake.extract_data.models.extraction_config import ExtractionConfig
from aje_libs.datalake.extract_data.orchestrators.extraction_orchestrator import (
    DataExtractionOrchestrator,
)
from aje_libs.datalake.shared.models import LoadMode, TableConfig, DatabaseConfig
from aje_libs.datalake.shared.exceptions import ProcessingError as ExtractionError


class DummyMonitor:
    def __init__(self) -> None:
        self.error_calls: List[Dict[str, Any]] = []

    def log_start(self, table_name: str, job_name: str, metadata: Dict[str, Any]) -> str:
        # Simular un process_id sin hacer nada más
        return "pid-1"

    def log_error(self, table_name: str, error_message: str, job_name: str, metadata: Dict[str, Any]):
        self.error_calls.append(
            {
                "table_name": table_name,
                "error_message": error_message,
                "job_name": job_name,
                "metadata": metadata,
            }
        )


@pytest.mark.unit
def test_extraction_orchestrator_execute_logs_and_raises_processing_error(monkeypatch):
    """
    Fuerza una excepción en _execute_extraction_strategy y valida que:
    - Se llame a monitor.log_error con metadata coherente.
    - Se relance ExtractionError.
    """

    extraction_config = ExtractionConfig(
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        table_name="tbl",
        max_threads=1,
        chunk_size=100,
        load_mode=LoadMode.NORMAL,
    )

    dummy_monitor = DummyMonitor()
    orchestrator = DataExtractionOrchestrator(
        extraction_config=extraction_config,
        monitor=dummy_monitor,
        process_guid="guid-1",
    )

    # Inicialización mínima sin tocar servicios reales
    def fake_initialize_components(self):
        self.monitor = dummy_monitor
        self.strategy = type("S", (), {"get_strategy_name": lambda self: "fake_strategy"})()
        self.table_config = TableConfig(stage_table_name="stg_tbl", source_table="tbl", load_type="full")
        self.database_config = DatabaseConfig(
            endpoint_name="endpoint",
            db_type="sqlserver",
            server="srv",
            database="db",
            username="user",
            secret_key="pwd",
            secret_name="secret",
            port=1433,
        )

    def fake_execute_extraction_strategy(self):
        raise RuntimeError("boom-strategy")

    monkeypatch.setattr(
        DataExtractionOrchestrator,
        "_initialize_components",
        fake_initialize_components,
    )
    monkeypatch.setattr(
        DataExtractionOrchestrator,
        "_execute_extraction_strategy",
        fake_execute_extraction_strategy,
    )

    with pytest.raises(ExtractionError):
        orchestrator.execute()

    assert len(dummy_monitor.error_calls) == 1
    call = dummy_monitor.error_calls[0]
    assert call["table_name"] == "tbl"
    # Solo validamos que se registró un mensaje de error de extracción,
    # sin acoplarnos al detalle interno del mensaje.
    assert call["error_message"].startswith("Extraction failed:")
    assert call["job_name"].startswith("extract_fake_strategy")
    assert call["metadata"]["load_mode"] == LoadMode.NORMAL.value


