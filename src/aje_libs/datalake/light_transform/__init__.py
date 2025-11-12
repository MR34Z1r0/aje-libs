"""
aje_libs.datalake.light_transform - Módulo de transformación ligera

Contiene toda la funcionalidad específica de transformación de datos en AWS Glue.
"""
from .models import ColumnMetadata, TableConfig, EndpointConfig, LightTransformConfig
from .factories import (
    LightTransformConfigFactory,
    LightTransformProcessorFactory,
)
from .orchestrators.light_transform_orchestrator import LightTransformOrchestrator
from .services.storage.delta_table_manager import DeltaTableWriter, TimeRangeDeleteManager
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
    'ColumnMetadata', 'TableConfig', 'EndpointConfig', 'LightTransformConfig',
    # Factories
    'LightTransformConfigFactory',
    'LightTransformProcessorFactory',
    # Orchestrators
    'LightTransformOrchestrator',
    # Services
    'ConfigurationService',
    'ExpressionParser',
    'TransformationEngine',
    'DeltaTableWriter',
    'TimeRangeDeleteManager',
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

