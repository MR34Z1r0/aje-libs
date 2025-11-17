from decimal import Decimal

import pytest

from aje_libs.datalake.light_transform.models import LightTransformResult


@pytest.mark.unit
def test_light_transform_result_to_dict_serializes_fields():
    result = LightTransformResult(
        success=True,
        table_name="tbl",
        records_processed=100,
        files_processed=["file1", "file2"],
        execution_time_seconds=1.5,
        load_mode="normal",
        error_message=None,
        warning_message="warn",
        metadata={"k": "v"},
        files_metadata=[{"file_size_mb": 1.0}],
        transformation_stats={"rows_filtered": 10},
    )

    as_dict = result.to_dict()

    assert as_dict["success"] is True
    assert as_dict["table_name"] == "tbl"
    assert as_dict["records_processed"] == 100
    assert as_dict["files_processed"] == ["file1", "file2"]
    assert as_dict["execution_time_seconds"] == 1.5
    assert as_dict["load_mode"] == "normal"
    assert as_dict["warning_message"] == "warn"
    assert as_dict["metadata"] == {"k": "v"}
    assert as_dict["files_metadata"] == [{"file_size_mb": 1.0}]
    assert as_dict["transformation_stats"] == {"rows_filtered": 10}


@pytest.mark.unit
def test_light_transform_result_get_total_size_mb_zero_when_no_metadata():
    result = LightTransformResult(
        success=True,
        table_name="tbl",
        records_processed=0,
        files_processed=[],
        execution_time_seconds=0.0,
        load_mode="normal",
        files_metadata=None,
    )

    assert result.get_total_size_mb() == Decimal("0.0")


@pytest.mark.unit
def test_light_transform_result_get_total_size_mb_sums_decimals():
    result = LightTransformResult(
        success=True,
        table_name="tbl",
        records_processed=0,
        files_processed=[],
        execution_time_seconds=0.0,
        load_mode="normal",
        files_metadata=[
            {"file_size_mb": 1.1},
            {"file_size_mb": 2.2},
        ],
    )

    total = result.get_total_size_mb()

    assert isinstance(total, Decimal)
    assert str(total) == str(Decimal("3.3"))


@pytest.mark.unit
def test_light_transform_result_get_average_file_size_mb_zero_when_no_files():
    result = LightTransformResult(
        success=True,
        table_name="tbl",
        records_processed=0,
        files_processed=[],
        execution_time_seconds=0.0,
        load_mode="normal",
        files_metadata=[],
    )

    assert result.get_average_file_size_mb() == Decimal("0.0")


@pytest.mark.unit
def test_light_transform_result_get_average_file_size_mb_calculates_average():
    result = LightTransformResult(
        success=True,
        table_name="tbl",
        records_processed=0,
        files_processed=[],
        execution_time_seconds=0.0,
        load_mode="normal",
        files_metadata=[
            {"file_size_mb": 1.0},
            {"file_size_mb": 3.0},
        ],
    )

    avg = result.get_average_file_size_mb()

    assert isinstance(avg, Decimal)
    assert str(avg) == str(Decimal("2.0"))


