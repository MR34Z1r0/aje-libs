"""
Excepciones de validación compartidas
"""
from .datalake_exception import DataLakeException

class ValidationException(DataLakeException):
    """Excepción para errores de validación de datos"""
    pass

class EmptyTableException(ValidationException):
    """Excepción cuando no hay datos para procesar"""
    pass

