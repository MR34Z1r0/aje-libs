"""
aje_libs.datalake.extract_data - Módulo de extracción de datos

Contiene toda la funcionalidad específica de extracción de datos.
"""
from .contracts import IExtractor, ILoader, IExtractionStrategy
from .models import (
    ExtractionConfig,
    ExtractionResult,
    DatabaseConfig,
    TableConfig,
    FileMetadata,
    LoadMode,
    ColumnMetadata,
    EndpointConfig,
)
from .factories import (
    ExtractorFactory,
    LoaderFactory,
    WatermarkStorageFactory,
    StrategyFactory,
    ConfigurationProviderFactory,
)
from .strategies import (
    ExtractionStrategy,
    ExtractionParams,
    ExtractionStrategyType,
    FullLoadStrategy,
    IncrementalStrategy,
    TimeRangeStrategy,
    StrategyRegistry,
    StrategyAdapter,
)
from .orchestrators.extraction_orchestrator import DataExtractionOrchestrator
from .services.query_builder import QueryBuilder
from .services.extractors import SQLServerExtractor
from .services.loaders import S3Loader
from .services.formatters import CSVFormatter, ParquetFormatter
from .services.watermark_storage import (
    CSVWatermarkStorage,
    DynamoDBWatermarkStorage,
    TransactionalWatermarkStorage,
    WatermarkStatus,
)
from .services.log_storage import DynamoDBLogStorage
from .services.monitoring import ExtractDataEventLoggerService
from .services.configuration import CsvExtractionConfigurationProvider

__all__ = [
    # Contracts
    'IExtractor', 'ILoader', 'IExtractionStrategy',
    # Models
    'ExtractionConfig',
    'ExtractionResult',
    'DatabaseConfig',
    'TableConfig',
    'FileMetadata',
    'LoadMode',
    'ColumnMetadata',
    'EndpointConfig',
    # Factories
    'ExtractorFactory',
    'LoaderFactory',
    'WatermarkStorageFactory',
    'StrategyFactory',
    'ConfigurationProviderFactory',
    # Strategies
    'ExtractionStrategy',
    'ExtractionParams',
    'ExtractionStrategyType',
    'FullLoadStrategy',
    'IncrementalStrategy',
    'TimeRangeStrategy',
    'StrategyRegistry',
    'StrategyAdapter',
    # Orchestrators
    'DataExtractionOrchestrator',
    # Services
    'QueryBuilder',
    'SQLServerExtractor',
    'S3Loader',
    'CSVFormatter',
    'ParquetFormatter',
    'CSVWatermarkStorage',
    'DynamoDBWatermarkStorage',
    'TransactionalWatermarkStorage',
    'WatermarkStatus',
    'DynamoDBLogStorage',
    'ExtractDataEventLoggerService',
    'CsvExtractionConfigurationProvider',
]
