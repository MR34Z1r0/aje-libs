"""
aje_libs.datalake.light_transform - Módulo de transformación ligera

Contiene toda la funcionalidad específica de transformación de datos en AWS Glue.
"""
from .models import ColumnMetadata, TableConfig, EndpointConfig
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
    'ColumnMetadata', 'TableConfig', 'EndpointConfig',
    'LightTransformException', 'ConfigurationError', 'ProcessingError',
    'TransformationException', 'TransformationWarningException',
    'DataValidationException', 'WatermarkError', 'MonitoringError',
    'EmptyTableException'
]

