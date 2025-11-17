"""
Estrategias de escritura para light_transform.
Proporciona diferentes estrategias según load_type (full, incremental, time_range).
"""
from .full_load_strategy import FullLoadStrategy
from .incremental_strategy import IncrementalStrategy
from .time_range_strategy import TimeRangeStrategy

__all__ = [
    'FullLoadStrategy',
    'IncrementalStrategy',
    'TimeRangeStrategy',
]

