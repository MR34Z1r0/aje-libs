"""
Contrato genérico para escritores de datos.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IDataWriter(ABC):
    """Define operaciones para escribir datos en destinos variados."""

    @abstractmethod
    def overwrite(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Sobrescribe datos en el destino."""

    @abstractmethod
    def append(self, df, path: str, partition_cols: Optional[List[str]] = None) -> None:
        """Inserta datos en modo append."""

    @abstractmethod
    def merge(self, df, path: str, merge_condition: str, partition_cols: Optional[List[str]] = None) -> None:
        """Realiza operaciones de merge/upsert."""

    @abstractmethod
    def write_time_range(
        self,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        time_range_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Operación específica para eliminar por rango y volver a escribir."""

    @abstractmethod
    def cleanup(self, path: str) -> None:
        """Elimina datos existentes en la ruta de destino."""


__all__ = ["IDataWriter"]

