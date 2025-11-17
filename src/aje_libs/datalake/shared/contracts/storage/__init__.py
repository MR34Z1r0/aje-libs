"""Contratos de almacenamiento compartidos."""

from .data_writer_interface import IDataWriter
from .storage_provider_interface import IStorageProvider

__all__ = [
    'IDataWriter',
    'IStorageProvider',
]
