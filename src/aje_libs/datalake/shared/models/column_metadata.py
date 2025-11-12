"""Metadatos compartidos para columnas de tablas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnMetadata:
    name: str
    column_id: int
    data_type: str
    transformation: str
    is_partition: bool = False
    is_id: bool = False
    is_order_by: bool = False
    is_filter_date: bool = False
    is_process_period: bool = False



