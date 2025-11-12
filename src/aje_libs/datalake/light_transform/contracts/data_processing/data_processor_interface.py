"""
Contrato para el procesador de datos de Light Transform.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from aje_libs.datalake.light_transform.contracts.configuration import ILightTransformConfig

class ILightTransformProcessor(ABC):
    """Define el comportamiento del procesador principal."""

    @abstractmethod
    def process_table(self, config: ILightTransformConfig) -> None:
        """Ejecuta la transformación para la configuración indicada."""


