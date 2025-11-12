"""
Excepciones genéricas para pipelines del datalake (extract / transform).
"""
from __future__ import annotations

from .datalake_exception import DataLakeException
from .validation_exception import ValidationException


class PipelineException(DataLakeException):
    """Excepción base para cualquier pipeline del datalake."""


class ConfigurationError(PipelineException):
    """Errores relacionados con la configuración de un pipeline."""


class ProcessingError(PipelineException):
    """Errores durante el procesamiento principal (transformaciones, escrituras, etc.)."""


class TransformationException(ProcessingError):
    """Error crítico durante las transformaciones de datos."""

    def __init__(self, column_name: str | None, message: str):
        self.column_name = column_name
        super().__init__(message)


class TransformationWarningException(ProcessingError):
    """Advertencias controladas durante la transformación (no detienen el pipeline)."""

    def __init__(self, warnings: list, message: str):
        self.warnings = warnings
        super().__init__(message)


class WatermarkError(ProcessingError):
    """Errores al gestionar watermarks (lectura, confirmación, limpieza)."""


class MonitoringError(PipelineException):
    """Errores al registrar métricas o logs en los sistemas de monitoreo."""


class DataValidationError(ValidationException):
    """Alias específico para validaciones de datos dentro del pipeline."""


__all__ = [
    "PipelineException",
    "ConfigurationError",
    "ProcessingError",
    "TransformationException",
    "TransformationWarningException",
    "WatermarkError",
    "MonitoringError",
    "DataValidationError",
]


