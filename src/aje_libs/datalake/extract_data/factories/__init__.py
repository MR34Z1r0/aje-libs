"""
Factories específicos de extract_data
"""
from .extractor_factory import ExtractorFactory
from .loader_factory import LoaderFactory
from .watermark_factory import WatermarkStorageFactory
from .strategy_factory import StrategyFactory

__all__ = [
    'ExtractorFactory',
    'LoaderFactory',
    'WatermarkStorageFactory',
    'StrategyFactory'
]

