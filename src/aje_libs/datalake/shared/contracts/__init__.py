"""Contratos compartidos del dominio datalake."""

from .configuration import ICsvLoader, IConfigurationProvider
from .data_access import IDataLoader
from .logging import ILogger, ILogStorage
from .monitoring import IMonitor, IEventLogger, INotificationService
from .storage import IDataWriter
from .cleanup import ICleanupService, IResourceCleaner
from .watermark import IWatermarkManager, IWatermarkStorage

__all__ = [
    'ICsvLoader',
    'IConfigurationProvider',
    'IDataLoader',
    'IDataWriter',
    'ILogger',
    'ILogStorage',
    'IMonitor',
    'IEventLogger',
    'INotificationService',
    'ICleanupService',
    'IResourceCleaner',
    'IWatermarkManager',
    'IWatermarkStorage',
]

