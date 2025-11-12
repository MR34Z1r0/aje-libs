"""
Contratos/Interfaces compartidas para watermark
"""
from .watermark_storage_interface import IWatermarkStorage
from .watermark_manager_interface import IWatermarkManager

__all__ = ['IWatermarkStorage', 'IWatermarkManager']

