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
    """Test que valida que partition_mode requiere partition_column cuando tiene un valor válido"""
    with pytest.raises(ValueError):
        TableConfig(stage_table_name="stg_table", partition_mode="daily", partition_column=None)

    # Caso válido
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="daily",
        partition_column="created_at",
    )
    assert cfg.partition_column == "created_at"


@pytest.mark.unit
def test_partition_mode_none_is_normalized():
    """Test que valida normalización de partition_mode='NONE' a None"""
    # 'NONE' se normaliza a None
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="NONE"
    )
    assert cfg.partition_mode is None
    
    # 'none' (minúsculas) también se normaliza
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="none"
    )
    assert cfg.partition_mode is None
    
    # String vacío se normaliza a None
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode=""
    )
    assert cfg.partition_mode is None


@pytest.mark.unit
def test_partition_mode_valid_values_are_normalized_to_uppercase():
    """Test que valida que valores válidos se normalizan a mayúsculas"""
    # 'AUTO' se mantiene en mayúsculas
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="AUTO",
        partition_column="created_at"
    )
    assert cfg.partition_mode == "AUTO"
    
    # 'auto' se normaliza a 'AUTO'
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="auto",
        partition_column="created_at"
    )
    assert cfg.partition_mode == "AUTO"
    
    # 'MIN_MAX' se mantiene en mayúsculas
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="MIN_MAX",
        partition_column="created_at"
    )
    assert cfg.partition_mode == "MIN_MAX"
    
    # 'min_max' se normaliza a 'MIN_MAX'
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="min_max",
        partition_column="created_at"
    )
    assert cfg.partition_mode == "MIN_MAX"


@pytest.mark.unit
def test_partition_mode_none_does_not_require_partition_column():
    """Test que valida que partition_mode=None no requiere partition_column"""
    # Cuando partition_mode es None, no se requiere partition_column
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode=None,
        partition_column=None
    )
    assert cfg.partition_mode is None
    assert cfg.partition_column is None
    
    # También funciona cuando partition_mode se normaliza a None
    cfg = TableConfig(
        stage_table_name="stg_table",
        partition_mode="NONE",
        partition_column=None
    )
    assert cfg.partition_mode is None
    assert cfg.partition_column is None


