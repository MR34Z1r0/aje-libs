"""
Excepciones de almacenamiento compartidas
"""
from .datalake_exception import DataLakeException

class StorageException(DataLakeException):
    """Excepción para errores de almacenamiento (S3, DynamoDB, etc.)"""
    pass

