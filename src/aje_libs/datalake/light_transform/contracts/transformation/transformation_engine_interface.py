"""
Contrato para el motor de transformaciones de Light Transform.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Tuple

from aje_libs.datalake.light_transform.models import ColumnMetadata


class ITransformationEngine(ABC):
    """Define las operaciones básicas del motor de transformaciones."""

    @abstractmethod
    def apply_transformations(self, df, columns_metadata: List[ColumnMetadata]) -> Tuple[Any, List[str]]:
        """Aplica transformaciones y retorna el DataFrame resultante junto a errores."""

    @abstractmethod
    def apply_post_processing(self, df, columns_metadata: List[ColumnMetadata]):
        """Aplica pasos posteriores (deduplicación, ordenamiento, etc.)."""


