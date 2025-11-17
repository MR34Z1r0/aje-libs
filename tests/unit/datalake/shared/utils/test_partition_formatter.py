from datetime import datetime

import pytest

from aje_libs.datalake.shared.utils.partition_formatter import PartitionFormatter


@pytest.mark.unit
def test_partition_formatter_default_format_uses_lima_timezone():
    formatter = PartitionFormatter()

    # Fecha fija sin tz; el formateador debe localizarla a TZ_LIMA
    ts = datetime(2024, 5, 10, 15, 30, 0)

    path = formatter.format_path(ts)

    # Formato por defecto: year={YYYY}/month={MM}/day={DD}
    assert path.startswith("year=2024/month=05/day=10")


@pytest.mark.unit
def test_partition_formatter_custom_format_with_quarter():
    formatter = PartitionFormatter("year={YYYY}/quarter={QUARTER}")
    ts = datetime(2024, 4, 1, 0, 0, 0)  # Abril -> Q2

    path = formatter.format_path(ts)

    assert path == "year=2024/quarter=Q2"


@pytest.mark.unit
def test_partition_formatter_raises_on_invalid_token():
    with pytest.raises(ValueError):
        PartitionFormatter("year={YYYY}/invalid={XX}")


@pytest.mark.unit
def test_extract_partition_values_and_parse_partition_path():
    path = "team=myteam/data_source=src/year=2024/month=05/day=10/"

    formatter = PartitionFormatter()
    values = formatter.extract_partition_values(path)

    assert values == {
        "team": "myteam",
        "data_source": "src",
        "year": "2024",
        "month": "05",
        "day": "10",
    }

    # Método de clase debe delegar a extract_partition_values
    values_cls = PartitionFormatter.parse_partition_path(path)
    assert values_cls == values


