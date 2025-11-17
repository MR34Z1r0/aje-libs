from decimal import Decimal

import pytest

from aje_libs.datalake.extract_data.models.extraction_result import ExtractionResult


@pytest.mark.unit
def test_to_dict_serializes_dates_and_metadata():
    result = ExtractionResult(
        success=True,
        table_name="test_table",
        records_extracted=10,
        files_created=["file1.parquet", "file2.parquet"],
        execution_time_seconds=1.23,
        strategy_used="test_strategy",
        error_message=None,
        metadata={"key": "value"},
        files_metadata=[{"file_size_mb": 1.5}],
    )

    as_dict = result.to_dict()

    assert as_dict["success"] is True
    assert as_dict["table_name"] == "test_table"
    assert as_dict["records_extracted"] == 10
    assert as_dict["files_created"] == ["file1.parquet", "file2.parquet"]
    assert as_dict["execution_time_seconds"] == 1.23
    assert as_dict["strategy_used"] == "test_strategy"
    assert as_dict["error_message"] is None
    assert as_dict["metadata"] == {"key": "value"}
    # start_time y end_time pueden ser None si no se pasan
    assert as_dict["start_time"] is None
    assert as_dict["end_time"] is None
    assert as_dict["files_metadata"] == [{"file_size_mb": 1.5}]


@pytest.mark.unit
def test_get_total_size_mb_returns_zero_when_no_metadata():
    result = ExtractionResult(
        success=True,
        table_name="test_table",
        records_extracted=0,
        files_created=[],
        execution_time_seconds=0.0,
        strategy_used="test_strategy",
        files_metadata=None,
    )

    assert result.get_total_size_mb() == Decimal("0.0")


@pytest.mark.unit
def test_get_total_size_mb_sums_sizes_as_decimal():
    result = ExtractionResult(
        success=True,
        table_name="test_table",
        records_extracted=0,
        files_created=[],
        execution_time_seconds=0.0,
        strategy_used="test_strategy",
        files_metadata=[
            {"file_size_mb": 1.1},
            {"file_size_mb": 2.2},
        ],
    )

    total = result.get_total_size_mb()

    assert isinstance(total, Decimal)
    # Comparar numéricamente, sin depender de la representación exacta del string
    assert abs(float(total) - 3.3) < 1e-9


@pytest.mark.unit
def test_get_average_file_size_mb_returns_zero_when_no_files():
    result = ExtractionResult(
        success=True,
        table_name="test_table",
        records_extracted=0,
        files_created=[],
        execution_time_seconds=0.0,
        strategy_used="test_strategy",
        files_metadata=[],
    )

    assert result.get_average_file_size_mb() == Decimal("0.0")


@pytest.mark.unit
def test_get_average_file_size_mb_calculates_average():
    result = ExtractionResult(
        success=True,
        table_name="test_table",
        records_extracted=0,
        files_created=[],
        execution_time_seconds=0.0,
        strategy_used="test_strategy",
        files_metadata=[
            {"file_size_mb": 1.0},
            {"file_size_mb": 3.0},
        ],
    )

    avg = result.get_average_file_size_mb()

    assert isinstance(avg, Decimal)
    assert str(avg) == str(Decimal("2.0"))


