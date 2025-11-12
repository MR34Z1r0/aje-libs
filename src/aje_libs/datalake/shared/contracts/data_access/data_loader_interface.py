"""
Contrato genérico para loaders de datos.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class IDataLoader(ABC):
    """Define la interfaz mínima para obtener datos de un origen."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Verifica si existen datos en la ruta indicada."""

    @abstractmethod
    def load(self, path: str):
        """Carga los datos desde la ruta y retorna un DataFrame/iterable."""


__all__ = ["IDataLoader"]

