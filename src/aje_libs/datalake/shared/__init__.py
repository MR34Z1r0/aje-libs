"""
aje_libs.datalake.shared - Componentes compartidos

Contiene servicios, contratos y utilidades compartidas entre extract_data y light_transform.
"""
# Exportar contratos
from .contracts import (
    ILogger, ILogStorage,
    IMonitor, IEventLogger, INotificationService,
    ICleanupService, IResourceCleaner,
    IWatermarkStorage, IWatermarkManager
)

# Exportar servicios
from .services import (
    LoggerService,
    MonitorService, EventLoggerService, NotificationService,
    CleanupService, S3CleanupService, DynamoDBCleanupService
)

# Exportar factories
from .factories import (
    LoggerFactory,
    MonitorFactory,
    CleanupFactory,
    WatermarkFactory
)

# Exportar modelos
from .models import (
    WatermarkStatus,
    ExecutionResult,
    ProcessMetadata
)

# Exportar excepciones
from .exceptions import (
    DataLakeException,
    ValidationException, EmptyTableException,
    ConfigurationException,
    StorageException
)

# Exportar utilidades
from .utils import PartitionFormatter

__all__ = [
    # Contratos
    'ILogger', 'ILogStorage',
    'IMonitor', 'IEventLogger', 'INotificationService',
    'ICleanupService', 'IResourceCleaner',
    'IWatermarkStorage', 'IWatermarkManager',
    # Servicios
    'LoggerService',
    'MonitorService', 'EventLoggerService', 'NotificationService',
    'CleanupService', 'S3CleanupService', 'DynamoDBCleanupService',
    # Factories
    'LoggerFactory',
    'MonitorFactory',
    'CleanupFactory',
    'WatermarkFactory',
    # Modelos
    'WatermarkStatus',
    'ExecutionResult',
    'ProcessMetadata',
    # Excepciones
    'DataLakeException',
    'ValidationException', 'EmptyTableException',
    'ConfigurationException',
    'StorageException',
    # Utilidades
    'PartitionFormatter'
]
