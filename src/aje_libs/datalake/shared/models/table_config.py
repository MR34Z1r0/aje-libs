"""Modelo de configuración de tablas reutilizable entre pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TableConfig:
    """Describe cómo debe procesarse una tabla origen/destino."""

    stage_table_name: str
    source_table: str = ""
    load_type: str = "full"

    source_schema: Optional[str] = None
    columns: Optional[str] = None
    source_table_type: Optional[str] = None

    partition_mode: Optional[str] = None
    partition_format: Optional[str] = None
    partition_column: Optional[str] = None
    id_column: Optional[str] = None

    filter_exp: Optional[str] = None
    filter_column: Optional[str] = None
    filter_data_type: Optional[str] = None
    join_expr: Optional[str] = None

    delay_incremental_ini: Optional[str] = None
    delay_incremental_end: Optional[str] = None
    start_value: Optional[str] = None
    end_value: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.stage_table_name:
            raise ValueError("stage_table_name es obligatorio en TableConfig")
        if not self.source_table:
            self.source_table = self.stage_table_name
        if not self.load_type:
            self.load_type = "full"


