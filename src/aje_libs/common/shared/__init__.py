"""
Código compartido no específico de ningún proveedor de cloud
"""
from .logger import custom_logger, set_logger_config
from .utils import DecimalEncoder

__all__ = [
    'custom_logger',
    'set_logger_config',
    'DecimalEncoder',
]

