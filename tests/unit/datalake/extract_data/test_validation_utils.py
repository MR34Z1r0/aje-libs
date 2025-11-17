import pytest

from aje_libs.datalake.extract_data.utils import validation_utils


@pytest.mark.unit
class TestValidateRequiredFields:
    def test_returns_empty_list_when_all_required_fields_present(self):
        data = {"a": "1", "b": "2"}
        required = ["a", "b"]

        result = validation_utils.validate_required_fields(data, required)

        assert result == []

    def test_detects_missing_and_empty_fields(self):
        data = {"a": "1", "b": "", "c": "  ", "d": None}
        required = ["a", "b", "c", "d", "e"]

        result = validation_utils.validate_required_fields(data, required)

        # b, c, d están vacíos o None; e no existe
        assert sorted(result) == ["b", "c", "d", "e"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "db_type,expected",
    [
        ("sqlserver", True),
        ("mssql", True),
        ("postgresql", True),
        ("postgres", True),
        ("oracle", True),
        ("mysql", True),
        ("mariadb", True),
        ("SQLSERVER", True),
        ("unknown", False),
        ("", False),
    ],
)
def test_validate_db_type(db_type, expected):
    assert validation_utils.validate_db_type(db_type) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "load_type,expected",
    [
        ("full", True),
        ("incremental", True),
        ("partitioned", True),
        ("date_range", True),
        ("between-date", True),
        ("FULL", True),
        ("invalid", False),
        ("", False),
    ],
)
def test_validate_load_type(load_type, expected):
    assert validation_utils.validate_load_type(load_type) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "fmt,expected",
    [
        ("parquet", True),
        ("csv", True),
        ("json", True),
        ("PARQUET", True),
        ("xml", False),
        ("", False),
    ],
)
def test_validate_output_format(fmt, expected):
    assert validation_utils.validate_output_format(fmt) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  col  ", "col"),
        ('"col"', "col"),
        ("'col'", "col"),
        ("  \"Columna Con Espacios\"  ", "Columna Con Espacios"),
    ],
)
def test_clean_column_name(raw, expected):
    assert validation_utils.clean_column_name(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "identifier,expected",
    [
        ("table_name", True),
        ("_column1", True),
        ("column_2", True),
        ("2column", False),
        ("column-name", False),
        ("column name", False),
        ("", False),
    ],
)
def test_validate_sql_identifier(identifier, expected):
    assert validation_utils.validate_sql_identifier(identifier) is expected


@pytest.mark.unit
def test_sanitize_query_parameter_handles_none():
    assert validation_utils.sanitize_query_parameter(None) == ""


@pytest.mark.unit
def test_sanitize_query_parameter_escapes_single_quotes_and_removes_dangerous_chars():
    raw = "O'Hara; DROP TABLE users --"

    sanitized = validation_utils.sanitize_query_parameter(raw)

    # Comprobamos las transformaciones clave
    assert "'" not in sanitized or "''" in sanitized
    assert ";" not in sanitized
    assert "--" not in sanitized


