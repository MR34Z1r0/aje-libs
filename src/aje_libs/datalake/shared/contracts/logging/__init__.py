"""
Contratos/Interfaces compartidas para logging
"""
from .logger_interface import ILogger
from .log_storage_interface import ILogStorage

__all__ = ['ILogger', 'ILogStorage']

