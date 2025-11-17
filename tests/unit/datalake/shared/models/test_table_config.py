import pytest

from aje_libs.datalake.shared.models import TableConfig


@pytest.mark.unit
def test_stage_table_name_is_mandatory():
    with pytest.raises(ValueError):
        TableConfig(stage_table_name="")  # type: ignore[arg-type]


@pytest.mark.unit
def test_source_table_defaults_to_stage_table_name_when_empty():
    cfg = TableConfig(stage_table_name="stg_table")

    assert cfg.source_table == "stg_table"


@pytest.mark.unit
def test_load_type_is_normalized_and_validated():
    cfg = TableConfig(stage_table_name="stg_table", load_type="FULL")

    assert cfg.load_type == "full"

    with pytest.raises(ValueError):
        TableConfig(stage_table_name="stg_table", load_type="invalid")


@pytest.mark.unit
def test_source_schema_blank_is_normalized_to_none():
    cfg = TableConfig(stage_table_name="stg_table", source_schema="  ")

    assert cfg.source_schema is None


@pytest.mark.unit
def test_incremental_requires_id_column():
    with pytest.raises(ValueError):
        TableConfig(stage_table_name="stg_table", load_type="incremental", id_column=None)

    # Caso válido
    cfg = TableConfig(stage_table_name="stg_table", load_type="incremental", id_column="id")
    assert cfg.id_column == "id"


@pytest.mark.unit
def test_partition_mode_requires_partition_column():
    with pytest.raises(ValueError):
        TableConfig(stage_table_name="stg_table", partition_mode="daily", partition_column=None)

    # Caso válido
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="daily",
        partition_column="created_at",
    )
    assert cfg.partition_column == "created_at"


