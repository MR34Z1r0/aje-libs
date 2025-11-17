from typing import Any, Dict, List, Optional

import pytest

from aje_libs.datalake.shared.services.monitoring import MonitorService


class DummyEventLogger:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.team = "team"
        self.data_source = "ds"
        self.endpoint_name = "endpoint"
        self.log_storage = None

    def log_process_status(self, status: str, message: str, table_name: str, job_name: str, context: Dict[str, Any]):
        call = {
            "status": status,
            "message": message,
            "table_name": table_name,
            "job_name": job_name,
            "context": context,
        }
        self.calls.append(call)
        return f"pid-{len(self.calls)}"


class DummyNotificationService:
    def __init__(self) -> None:
        self.errors: List[Dict[str, Any]] = []

    def send_error_notification(self, error_message: str, context: Dict[str, Any]) -> None:
        self.errors.append({"error_message": error_message, "context": context})


class DummyLogger:
    def __init__(self) -> None:
        self.infos: List[Any] = []
        self.errors: List[Any] = []
        self.warnings: List[Any] = []

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.infos.append((message, extra))

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.errors.append((message, extra))

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.warnings.append((message, extra))


@pytest.mark.unit
def test_monitor_service_log_start_success():
    event_logger = DummyEventLogger()
    logger = DummyLogger()
    monitor = MonitorService(event_logger=event_logger, notification_service=None, logger=logger)

    pid = monitor.log_start("tbl", job_name="job", metadata={"k": "v"})

    assert pid == "pid-1"
    assert len(event_logger.calls) == 1
    call = event_logger.calls[0]
    assert call["status"] == "RUNNING"
    assert call["table_name"] == "tbl"
    assert call["job_name"] == "job"
    assert call["context"]["k"] == "v"
    assert logger.infos, "Debe loguear info"


@pytest.mark.unit
def test_monitor_service_log_success_and_error_notification():
    event_logger = DummyEventLogger()
    notif = DummyNotificationService()
    logger = DummyLogger()
    monitor = MonitorService(event_logger=event_logger, notification_service=notif, logger=logger)

    pid_ok = monitor.log_success("tbl", job_name="job_ok", metadata={"ok": True})
    pid_err = monitor.log_error("tbl", "boom", job_name="job_err", metadata={"x": 1})

    assert pid_ok == "pid-1"
    assert pid_err == "pid-2"
    assert len(event_logger.calls) == 2
    assert event_logger.calls[0]["status"] == "SUCCESS"
    assert event_logger.calls[1]["status"] == "FAILED"

    # Debe enviar notificación de error
    assert len(notif.errors) == 1
    err = notif.errors[0]
    assert err["error_message"] == "boom"
    assert err["context"]["table_name"] == "tbl"
    assert err["context"]["job_name"] == "job_err"
    assert err["context"]["x"] == 1


@pytest.mark.unit
def test_monitor_service_log_warning():
    event_logger = DummyEventLogger()
    logger = DummyLogger()
    monitor = MonitorService(event_logger=event_logger, notification_service=None, logger=logger)

    pid = monitor.log_warning("tbl", "warn-msg", job_name="job_warn", metadata={"w": 2})

    assert pid == "pid-1"
    assert event_logger.calls[0]["status"] == "WARNING"
    assert logger.warnings, "Debe registrar warning"


@pytest.mark.unit
def test_monitor_service_cleanup_table_logs_uses_event_logger_when_log_storage_missing():
    class EventLoggerWithCleanup(DummyEventLogger):
        def __init__(self) -> None:
            super().__init__()
            self.cleanup_calls: List[Any] = []

        def cleanup_table_logs(self, table_name: str):
            self.cleanup_calls.append(table_name)
            return {"success": True, "items_deleted": 10}

    event_logger = EventLoggerWithCleanup()
    logger = DummyLogger()
    monitor = MonitorService(event_logger=event_logger, notification_service=None, logger=logger)

    result = monitor.cleanup_table_logs("tbl")

    assert result["success"] is True
    assert result["items_deleted"] == 10
    assert event_logger.cleanup_calls == ["tbl"]


