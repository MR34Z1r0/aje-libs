"""
aje_libs.datalake.light_transform - Módulo de transformación ligera

Contiene toda la funcionalidad específica de transformación de datos en AWS Glue.
"""
from .models import LightTransformConfig, LightTransformResult
from aje_libs.datalake.shared.models import ColumnMetadata, TableConfig, EndpointConfig  # ✅ Movidos a shared/models
from .factories import (
    LightTransformConfigFactory,
    LightTransformProcessorFactory,
    DefaultLightTransformComponentFactory,  # ✅ Nueva factory
)
from .orchestrators.light_transform_orchestrator import LightTransformOrchestrator
from .strategies import (
    WriteStrategyFactory,  # ✅ Factory de estrategias de escritura
    WriteStrategyValidator,  # ✅ Validador de estrategias de escritura
)
from .services.storage.delta import DeltaTableWriter, TimeRangeDeleteManager as DeltaTimeRangeDeleteManager
from .services.storage.iceberg import IcebergTableWriter, TimeRangeDeleteManager as IcebergTimeRangeDeleteManager
from .services.storage.parquet import ParquetTableWriter
from .services import (
    ConfigurationService,
    ExpressionParser,
    TransformationEngine,
    DataLakeLogger,
    DynamoDBLogger,
    Monitor,
    DynamoDBWatermarkHelper,
    DataProcessor,
)
from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConfigurationError,
    DataValidationError as DataValidationException,
    EmptyTableException,
    PipelineException as LightTransformException,
    MonitoringError,
    ProcessingError,
    TransformationException,
    TransformationWarningException,
    WatermarkError,
)

__all__ = [
    # Models
    'LightTransformConfig', 'LightTransformResult',
    'ColumnMetadata', 'TableConfig', 'EndpointConfig',  # ✅ Reexportados desde shared/models para compatibilidad
    # Factories
    'LightTransformConfigFactory',
    'LightTransformProcessorFactory',
    'DefaultLightTransformComponentFactory',  # ✅ Nueva factory
    # Orchestrators
    'LightTransformOrchestrator',
    # Strategies
    'WriteStrategyFactory',  # ✅ Factory de estrategias de escritura
    'WriteStrategyValidator',  # ✅ Validador de estrategias de escritura
    # Services
    'ConfigurationService',
    'ExpressionParser',
    'TransformationEngine',
    # Delta Lake
    'DeltaTableWriter',
    'DeltaTimeRangeDeleteManager',
    # Apache Iceberg
    'IcebergTableWriter',
    'IcebergTimeRangeDeleteManager',
    # PySpark puro (Parquet)
    'ParquetTableWriter',
    'DataLakeLogger',
    'DynamoDBLogger',
    'Monitor',
    'DynamoDBWatermarkHelper',
    'DataProcessor',
    # Exceptions
    'LightTransformException', 'ConfigurationError', 'ProcessingError',
    'TransformationException', 'TransformationWarningException',
    'DataValidationException', 'WatermarkError', 'MonitoringError',
    'EmptyTableException'
]

