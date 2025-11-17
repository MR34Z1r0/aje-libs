import logging
import os
from pathlib import Path

import pytest

from aje_libs.datalake.shared.services.logging import LoggerService


@pytest.mark.unit
def test_logger_service_creates_local_logger_and_writes_to_console_and_file(tmp_path, monkeypatch, capsys):
    # Configurar directorio de logs temporal
    log_dir = tmp_path / "logs"

    # Forzar modo local (no AWS)
    monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("GLUE_VERSION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    LoggerService.configure_global(
        log_level=logging.INFO,
        log_directory=str(log_dir),
        service_name="test_service",
        force_local_mode=True,
    )

    logger = LoggerService.get_logger("test_logger_service")
    logger.info("mensaje de prueba")

    # Debe escribir algo a stdout (console handler)
    captured = capsys.readouterr()
    assert "mensaje de prueba" in captured.out or "mensaje de prueba" in captured.err

    # Debe haberse creado un archivo de log
    files = list(log_dir.glob("test_service_*.log"))
    assert files, "No se creó archivo de log"


@pytest.mark.unit
def test_logger_service_print_environment_info_does_not_crash(capsys, monkeypatch, tmp_path):
    # Config mínima
    LoggerService.configure_global(
        log_level=logging.DEBUG,
        log_directory=str(tmp_path / "logs"),
        service_name="env_test",
        force_local_mode=True,
    )

    LoggerService.print_environment_info()

    out = capsys.readouterr().out
    assert "DATALAKE LOGGING ENVIRONMENT INFO" in out
    assert "Service Name: env_test" in out


