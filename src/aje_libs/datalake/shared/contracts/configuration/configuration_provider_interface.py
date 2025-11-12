"""
Contrato genérico para proveedores de configuración.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IConfigurationProvider(ABC):
    """Define operaciones para obtener configuraciones de tablas y endpoints."""

    @abstractmethod
    def get_table_config(self, table_name: str, tables_source: str, **filters):
        """Retorna la configuración de una tabla."""

    @abstractmethod
    def get_endpoint_config(self, endpoint_name: str, endpoints_source: str, **filters):
        """Retorna la configuración del endpoint."""

    @abstractmethod
    def get_columns_metadata(self, table_name: str, columns_source: str, **filters) -> List[Dict[str, Any]]:
        """Retorna los metadatos de columnas."""


__all__ = ["IConfigurationProvider"]

