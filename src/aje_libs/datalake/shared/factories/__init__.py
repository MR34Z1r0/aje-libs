"""
Factories compartidas - Exportaciones principales
"""
from .logger_factory import LoggerFactory
from .monitor_factory import MonitorFactory
from .cleanup_factory import CleanupFactory
from .watermark_factory import WatermarkFactory
from .event_logger_builder import EventLoggerBuilder  # ✅ Nuevo builder
from .notification_service_builder import NotificationServiceBuilder  # ✅ Nuevo builder
from .table_writer_factory import TableWriterFactory  # ✅ Factory para table writers (Delta, Iceberg)
from .secret_provider_factory import SecretProviderFactory  # ✅ Factory para proveedores de secretos
from .storage_provider_factory import StorageProviderFactory  # ✅ Factory para proveedores de almacenamiento
from .database_provider_factory import DatabaseProviderFactory  # ✅ Factory para proveedores de bases de datos

__all__ = [
    'LoggerFactory',
    'MonitorFactory',
    'CleanupFactory',
    'WatermarkFactory',
    'EventLoggerBuilder',  # ✅ Nuevo builder
    'NotificationServiceBuilder',  # ✅ Nuevo builder
    'TableWriterFactory',  # ✅ Factory para table writers
    'SecretProviderFactory',  # ✅ Factory para proveedores de secretos
    'StorageProviderFactory',  # ✅ Factory para proveedores de almacenamiento
    'DatabaseProviderFactory',  # ✅ Factory para proveedores de bases de datos
]
