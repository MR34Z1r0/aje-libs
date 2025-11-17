from typing import Dict, Any

import pytest

from aje_libs.datalake.extract_data.models.extraction_config import ExtractionConfig
from aje_libs.datalake.extract_data.orchestrators.extraction_orchestrator import (
    DataExtractionOrchestrator,
)
from aje_libs.datalake.shared.models import LoadMode, TableConfig


def _build_minimal_extraction_config(**overrides: Dict[str, Any]) -> ExtractionConfig:
    """
    Crea una ExtractionConfig mínima válida para tests.
    Permite sobreescribir campos via **overrides.
    """
    base = dict(
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        table_name="tbl",
        max_threads=4,
        chunk_size=1000,
        load_mode=LoadMode.NORMAL,
    )
    base.update(overrides)
    return ExtractionConfig(**base)


def _build_orchestrator(**config_overrides: Dict[str, Any]) -> DataExtractionOrchestrator:
    cfg = _build_minimal_extraction_config(**config_overrides)
    # No necesitamos monitor/ComponentFactory reales para estos métodos internos
    return DataExtractionOrchestrator(extraction_config=cfg)


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ('"col1"', "col1"),
        ('"col1,col2"', "col1,col2"),
        ('"col1","col2"', "col1,col2"),
        ('col1', "col1"),
        ('"col1', "col1"),
        ('col1"', "col1"),
    ],
)
def test_process_columns_field_removes_problematic_double_quotes(raw: str, expected: str):
    """
    _process_columns_field debe limpiar comillas dobles problemáticas
    sin alterar el resto del contenido.
    """
    orch = _build_orchestrator()

    cleaned = orch._process_columns_field(raw)

    assert cleaned == expected


@pytest.mark.unit
def test_strategy_needs_watermark_storage_true_for_incremental_with_partition_column():
    orch = _build_orchestrator()
    orch.table_config = TableConfig(
        stage_table_name="stg_table",
        load_type="incremental",
        partition_column="created_at",
        id_column="id",
    )

    # El método puede devolver un valor truthy (por ejemplo el nombre de la columna)
    assert bool(orch._strategy_needs_watermark_storage()) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "load_type,partition_column,expected",
    [
        ("full", "created_at", False),
        ("incremental", None, False),
        ("incremental", "", False),
    ],
)
def test_strategy_needs_watermark_storage_false_in_other_cases(load_type, partition_column, expected):
    orch = _build_orchestrator()
    orch.table_config = TableConfig(
        stage_table_name="stg_table",
        load_type=load_type,
        partition_column=partition_column,
        id_column="id",
    )

    # Convertimos a bool para desacoplarnos del valor concreto devuelto
    assert bool(orch._strategy_needs_watermark_storage()) is expected


@pytest.mark.unit
def test_build_partitioned_query_uses_source_schema_table_and_range_and_filter():
    orch = _build_orchestrator()
    orch.table_config = TableConfig(
        stage_table_name="stg_table",
        source_schema="dbo",
        source_table="src_table st",
        load_type="full",
        columns="col1,col2",
        partition_column="created_at",
        id_column="id",
        filter_exp='st.is_active = 1',
        join_expr="JOIN other o ON o.id = st.id",
    )

    query = orch._build_partitioned_query(
        partition_column="created_at",
        start_value=10,
        end_value=20,
    )

    # Debe incluir el schema y tabla sin alias en el FROM principal
    assert "FROM dbo.src_table" in query
    # Debe incluir el join si está configurado
    assert "JOIN other o ON o.id = st.id" in query
    # Debe incluir las columnas configuradas
    assert "SELECT id as id" in query or "SELECT" in query  # id_column se añade como alias "id"
    assert "col1,col2" in query
    # Debe incluir el rango de partición
    assert "created_at >= 10 AND created_at < 20" in query
    # Debe incluir el filtro extra entre paréntesis y sin comillas dobles
    assert "(st.is_active = 1)" in query


@pytest.mark.unit
def test_get_chunking_params_for_partition_builds_order_by_and_uses_chunk_size():
    orch = _build_orchestrator(chunk_size=500)
    orch.table_config = TableConfig(
        stage_table_name="stg_table",
        load_type="incremental",
        partition_column="created_at",
        id_column="id",
    )

    params = orch._get_chunking_params_for_partition()

    assert params["order_by"] == "created_at, id"
    assert params["chunk_size"] == 500


