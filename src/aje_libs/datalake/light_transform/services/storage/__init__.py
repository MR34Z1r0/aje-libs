"""
Servicios de almacenamiento para light_transform.
"""

from .delta_table_manager import TimeRangeDeleteManager, DeltaTableWriter

__all__ = [
    'TimeRangeDeleteManager',
    'DeltaTableWriter',
]

