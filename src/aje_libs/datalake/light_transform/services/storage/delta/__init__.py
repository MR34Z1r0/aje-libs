"""
Módulo de soporte para Delta Lake.
Proporciona implementación de IDataWriter y utilidades para tablas Delta Lake.
"""
from .delta_table_writer import DeltaTableWriter
from .delta_table_manager import TimeRangeDeleteManager

__all__ = [
    'DeltaTableWriter',
    'TimeRangeDeleteManager',
]

