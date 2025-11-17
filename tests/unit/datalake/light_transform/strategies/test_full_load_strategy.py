import pytest

# Saltar módulo completo si pyspark no está disponible, ya que light_transform lo requiere al importarse
pytest.importorskip("pyspark", reason="pyspark requerido para tests de estrategias de light_transform")

from aje_libs.datalake.light_transform.strategies.write_strategies.full_load_strategy import (
    FullLoadStrategy,
)


class DummyDataFrame:
    def __init__(self, count_value: int):
        self._count_value = count_value

    def count(self) -> int:
        return self._count_value


class DummyDataWriter:
    def __init__(self):
        self.overwrite_calls = []

    def overwrite(self, df, path, partition_cols=None):
        self.overwrite_calls.append(
            {
                "df": df,
                "path": path,
                "partition_cols": partition_cols,
            }
        )


@pytest.mark.unit
def test_full_load_strategy_raises_when_df_is_none():
    strategy = FullLoadStrategy()

    with pytest.raises(ValueError):
        strategy.execute(data_writer=DummyDataWriter(), df=None, path="s3://bucket/table")


@pytest.mark.unit
def test_full_load_strategy_executes_overwrite_and_returns_name_and_flags(monkeypatch):
    strategy = FullLoadStrategy()
    df = DummyDataFrame(count_value=10)
    writer = DummyDataWriter()

    # Evitar logging real
    class DummyLogger:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "aje_libs.datalake.light_transform.strategies.write_strategies.full_load_strategy.LoggerService.get_logger",  # noqa: E501
        lambda *_args, **_kwargs: DummyLogger(),
    )

    strategy.execute(
        data_writer=writer,
        df=df,
        path="s3://bucket/table",
        partition_cols=["year", "month"],
    )

    assert len(writer.overwrite_calls) == 1
    call = writer.overwrite_calls[0]
    assert call["path"] == "s3://bucket/table"
    assert call["partition_cols"] == ["year", "month"]

    assert strategy.get_strategy_name() == "full_load"
    assert strategy.requires_id_columns() is False
    assert strategy.requires_period_column() is False


