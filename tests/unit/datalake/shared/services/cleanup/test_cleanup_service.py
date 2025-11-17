import pytest

from aje_libs.datalake.shared.services.cleanup.cleanup_service import CleanupService


class DummyCleaner:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.calls = []

    def delete_objects(self, resource_path, filters=None):
        self.calls.append((resource_path, filters))
        if self.should_fail:
            raise RuntimeError(f"{self.name} failure")
        return {
            "success": True,
            "items_deleted": 5,
            "errors": [],
            "service": self.name,
        }


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg: str):
        self.errors.append(msg)


@pytest.mark.unit
def test_cleanup_service_aggregates_results_from_cleaners():
    cleaner1 = DummyCleaner("c1")
    cleaner2 = DummyCleaner("c2")
    service = CleanupService(resource_cleaners=[cleaner1, cleaner2], logger=None)

    result = service.cleanup("s3://bucket/path", filters={"table": "t"})

    assert result["success"] is True
    assert result["total_items_deleted"] == 10
    assert len(result["services_results"]) == 2
    assert not result["errors"]

    assert cleaner1.calls and cleaner2.calls


@pytest.mark.unit
def test_cleanup_service_handles_cleaner_exceptions_and_logs():
    cleaner_ok = DummyCleaner("ok")
    cleaner_fail = DummyCleaner("fail", should_fail=True)
    logger = DummyLogger()

    service = CleanupService(resource_cleaners=[cleaner_ok, cleaner_fail], logger=logger)

    result = service.cleanup("path")

    assert result["success"] is False
    assert result["total_items_deleted"] == 5  # solo del cleaner_ok
    assert result["errors"]
    assert any("fail" in e for e in result["errors"])
    assert logger.errors, "Debe loguear errores"


@pytest.mark.unit
def test_cleanup_table_data_delegates_to_cleanup():
    cleaner = DummyCleaner("c1")
    service = CleanupService(resource_cleaners=[cleaner], logger=None)

    result = service.cleanup_table_data("table/path")

    assert result["success"] is True
    assert cleaner.calls[0][0] == "table/path"


