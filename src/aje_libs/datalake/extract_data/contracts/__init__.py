"""
Contratos/Interfaces específicas de extract_data
"""
from .extractor_interface import IExtractor
from .loader_interface import ILoader
from .strategy_interface import IExtractionStrategy

__all__ = ['IExtractor', 'ILoader', 'IExtractionStrategy']

