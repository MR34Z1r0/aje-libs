"""
Contratos/Interfaces compartidas para cleanup
"""
from .cleanup_service_interface import ICleanupService
from .resource_cleaner_interface import IResourceCleaner

__all__ = ['ICleanupService', 'IResourceCleaner']

