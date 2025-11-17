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
# SparkConfigBuilder se importa de forma diferida para evitar requerir pyspark en extract_data
# from .utils.spark_config_builder import SparkConfigBuilder  # ✅ Builder para configuraciones de Spark (import diferido)

# Exportar builders
from .builders import DatabaseConfigBuilder

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
           'PartitionFormatter',
           # 'SparkConfigBuilder',  # ✅ Builder para configuraciones de Spark (import diferido - solo para light_transform)
    # Builders
    'DatabaseConfigBuilder',  # ✅ Nuevo builder
]
