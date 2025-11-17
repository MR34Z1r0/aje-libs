"""
Contratos/Interfaces específicas de extract_data
"""
from .extractor_interface import IExtractor
from .loader_interface import ILoader
from .strategy_interface import IExtractionStrategy
from .formatter_interface import IFormatter
from .query_builder_interface import IQueryBuilder

__all__ = ['IExtractor', 'ILoader', 'IExtractionStrategy', 'IFormatter', 'IQueryBuilder']

