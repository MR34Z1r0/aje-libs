import pytest

from aje_libs.datalake.shared.models import LoadMode


@pytest.mark.unit
def test_load_mode_from_string_valid_values():
    assert LoadMode.from_string("initial") is LoadMode.INITIAL
    assert LoadMode.from_string("NORMAL") is LoadMode.NORMAL
    assert LoadMode.from_string(" reset ") is LoadMode.RESET
    assert LoadMode.from_string("reprocess") is LoadMode.REPROCESS


@pytest.mark.unit
def test_load_mode_from_string_invalid_value_raises():
    with pytest.raises(ValueError):
        LoadMode.from_string("unknown-mode")


