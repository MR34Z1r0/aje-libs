"""
Excepciones de configuración compartidas
"""
from .datalake_exception import DataLakeException

class ConfigurationException(DataLakeException):
    """Excepción para errores de configuración"""
    pass

