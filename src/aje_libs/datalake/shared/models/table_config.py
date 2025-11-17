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
        """
        Valida y normaliza la configuración de tabla.
        
        Raises:
            ValueError: Si stage_table_name está vacío o load_type es inválido.
        """
        # Validar stage_table_name
        if not self.stage_table_name or not self.stage_table_name.strip():
            raise ValueError("stage_table_name es obligatorio en TableConfig")
        
        # Normalizar stage_table_name
        if self.stage_table_name != self.stage_table_name.strip():
            object.__setattr__(self, 'stage_table_name', self.stage_table_name.strip())
        
        # Normalizar source_table
        if not self.source_table or not self.source_table.strip():
            object.__setattr__(self, 'source_table', self.stage_table_name)
        elif self.source_table != self.source_table.strip():
            object.__setattr__(self, 'source_table', self.source_table.strip())
        
        # Validar y normalizar load_type
        valid_load_types = ['full', 'incremental', 'partitioned', 'date_range', 'between-date']
        load_type_lower = (self.load_type or 'full').lower()
        
        if load_type_lower not in valid_load_types:
            raise ValueError(
                f"load_type '{self.load_type}' no es válido. "
                f"Disponibles: {', '.join(valid_load_types)}"
            )
        
        if load_type_lower != self.load_type:
            object.__setattr__(self, 'load_type', load_type_lower)
        
        # Validar source_schema si está presente
        if self.source_schema is not None and not self.source_schema.strip():
            object.__setattr__(self, 'source_schema', None)
        
        # Validar id_column si load_type es incremental
        if load_type_lower == 'incremental' and not self.id_column:
            raise ValueError(
                "id_column es requerido cuando load_type es 'incremental'"
            )
        
        # Validar partition_column si partition_mode está configurado
        if self.partition_mode and not self.partition_column:
            raise ValueError(
                "partition_column es requerido cuando partition_mode está configurado"
            )


