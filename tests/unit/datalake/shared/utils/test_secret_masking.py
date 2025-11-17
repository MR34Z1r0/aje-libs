import pytest

from aje_libs.datalake.shared.utils import secret_masking


@pytest.mark.unit
def test_mask_secret_basic_behavior():
    assert secret_masking.mask_secret("") == "***"
    assert secret_masking.mask_secret("abc") == "***"
    assert secret_masking.mask_secret("abcdef", visible_chars=2) == "****ef"


@pytest.mark.unit
def test_mask_secret_partial_behavior():
    masked = secret_masking.mask_secret_partial("my_secret_password_123", visible_start=2, visible_end=3)
    assert masked.startswith("my")
    assert masked.endswith("123")
    assert "*" in masked[2:-3]


@pytest.mark.unit
def test_mask_dict_secrets_masks_nested_keys():
    data = {
        "username": "user",
        "password": "supersecret",
        "nested": {
            "api_key": "1234567890",
        },
        "other": "value",
    }

    masked = secret_masking.mask_dict_secrets(data)

    assert masked["username"] == "user"
    assert masked["other"] == "value"
    assert masked["password"] != "supersecret"
    assert "*" in masked["password"]
    assert masked["nested"]["api_key"] != "1234567890"


@pytest.mark.unit
def test_sanitize_log_message_masks_common_patterns():
    message = (
        'Connecting with password=supersecret, '
        'token: abcdefg, '
        'api_key="KEY12345" and ACCESS_key = anothersecret'
    )

    sanitized = secret_masking.sanitize_log_message(message)

    # Los valores originales no deben aparecer
    assert "supersecret" not in sanitized
    assert "abcdefg" not in sanitized
    assert "KEY12345" not in sanitized
    assert "anothersecret" not in sanitized


@pytest.mark.unit
def test_is_secret_key_detects_probable_secret_names():
    assert secret_masking.is_secret_key("PASSWORD")
    assert secret_masking.is_secret_key("db_secret_key")
    assert secret_masking.is_secret_key("api_key")
    assert not secret_masking.is_secret_key("username")
    assert not secret_masking.is_secret_key("host")


