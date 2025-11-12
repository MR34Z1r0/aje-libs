"""
Excepción base del datalake
"""
class DataLakeException(Exception):
    """Excepción base para todas las excepciones del datalake"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

