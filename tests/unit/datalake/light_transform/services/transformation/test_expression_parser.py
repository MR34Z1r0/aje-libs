import pytest

from aje_libs.datalake.light_transform.services.transformation.expression_parser import (
    ExpressionParser,
)


@pytest.mark.unit
def test_expression_parser_simple_column_when_no_function():
    parser = ExpressionParser()

    result = parser.parse_transformation("my_column")

    assert result == [("simple_column", ["my_column"])]


@pytest.mark.unit
def test_expression_parser_empty_expression_returns_empty_list():
    parser = ExpressionParser()

    assert parser.parse_transformation("") == []
    assert parser.parse_transformation("   ") == []


@pytest.mark.unit
def test_expression_parser_single_function_with_simple_params():
    parser = ExpressionParser()

    result = parser.parse_transformation('fn_upper(trim(col1))')

    # parse_transformation devuelve solo la función externa y sus parámetros “crudos”
    assert len(result) == 1
    func_name, params = result[0]
    assert func_name == "fn_upper"
    assert params == ["trim(col1)"]


@pytest.mark.unit
def test_expression_parser_extract_parameters_handles_commas_and_quotes():
    parser = ExpressionParser()

    params = parser._extract_parameters('col1, "valor, con, comas", fn_nested(col2, col3)')

    assert params[0] == "col1"
    assert params[1] == '"valor, con, comas"'
    assert params[2] == "fn_nested(col2, col3)"


