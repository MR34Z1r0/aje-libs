import io

import pytest
from botocore.exceptions import ClientError

from aje_libs.datalake.shared.services.storage.s3_storage_provider import S3StorageProvider


class DummyS3Helper:
    def __init__(self):
        self.put_calls = []
        self.delete_calls = []
        self.list_calls = []
        self.exists_calls = []
        self.should_raise = False

    def put_object(self, object_key, body, extra_args=None):
        if self.should_raise:
            raise ClientError(
                error_response={"Error": {"Code": "500", "Message": "boom"}},
                operation_name="PutObject",
            )
        self.put_calls.append((object_key, body, extra_args))
        return f"s3://bucket/{object_key}"

    def delete_objects(self, object_keys):
        if self.should_raise:
            raise ClientError(
                error_response={"Error": {"Code": "500", "Message": "boom"}},
                operation_name="DeleteObjects",
            )
        self.delete_calls.append(list(object_keys))
        return {"success": True, "items_deleted": len(object_keys)}

    def list_objects(self, prefix, max_keys=None):
        if self.should_raise:
            raise ClientError(
                error_response={"Error": {"Code": "500", "Message": "boom"}},
                operation_name="ListObjectsV2",
            )
        self.list_calls.append((prefix, max_keys))
        return [{"Key": f"{prefix}/file1"}]

    def object_exists(self, object_key):
        self.exists_calls.append(object_key)
        if self.should_raise:
            raise ClientError(
                error_response={"Error": {"Code": "404", "Message": "not found"}},
                operation_name="HeadObject",
            )
        return True


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


@pytest.fixture
def s3_provider(monkeypatch):
    dummy_logger = DummyLogger()

    # Evitar LoggerService real
    monkeypatch.setattr(
        "aje_libs.datalake.shared.services.storage.s3_storage_provider.LoggerService.get_logger",
        lambda *_args, **_kwargs: dummy_logger,
    )

    # Evitar que S3Helper real haga llamadas a AWS al construir el provider
    dummy_helper = DummyS3Helper()

    def fake_s3_helper_ctor(bucket_name, region_name=None):
        # ignorar argumentos y devolver siempre el mismo helper en memoria
        return dummy_helper

    monkeypatch.setattr(
        "aje_libs.datalake.shared.services.storage.s3_storage_provider.S3Helper",
        fake_s3_helper_ctor,
    )

    provider = S3StorageProvider(bucket_name="bucket", region="us-east-1")
    # Guardar referencias para que los tests las usen sin tocar atributos reales
    provider._test_logger = dummy_logger  # type: ignore[attr-defined]
    provider._test_helper = dummy_helper  # type: ignore[attr-defined]
    return provider


@pytest.mark.unit
def test_s3_storage_provider_put_delete_list_and_exists_ok(s3_provider):
    helper = s3_provider._test_helper  # type: ignore[attr-defined]

    # put_object
    path = s3_provider.put_object("path/file.txt", body=b"data", extra_args={"ContentType": "text/plain"})
    assert path.endswith("path/file.txt")
    assert helper.put_calls[0][0] == "path/file.txt"

    # delete_objects
    del_result = s3_provider.delete_objects(["a", "b"])
    assert del_result["success"] is True
    assert del_result["items_deleted"] == 2

    # list_objects
    listed = s3_provider.list_objects("prefix", max_keys=10)
    assert listed and listed[0]["Key"].startswith("prefix/")

    # object_exists
    assert s3_provider.object_exists("some/key") is True
    assert helper.exists_calls == ["some/key"]


@pytest.mark.unit
def test_s3_storage_provider_handles_client_error_and_logs(s3_provider):
    helper = s3_provider._test_helper  # type: ignore[attr-defined]
    helper.should_raise = True
    logger = s3_provider._test_logger  # type: ignore[attr-defined]

    with pytest.raises(ClientError):
        s3_provider.put_object("k", body="x")
    assert logger.errors, "Debe registrar error en put_object"

    with pytest.raises(ClientError):
        s3_provider.delete_objects(["k1"])
    assert len(logger.errors) >= 2

    with pytest.raises(ClientError):
        s3_provider.list_objects("p")
    assert len(logger.errors) >= 3

    # object_exists debe capturar la excepción y devolver False
    assert s3_provider.object_exists("nope") is False


