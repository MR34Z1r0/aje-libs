"""
Contrato para cargadores de archivos CSV utilizados en la configuración.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ICsvLoader(ABC):
    """Define la interfaz para cargar contenido de CSV desde diferentes orígenes."""

    @abstractmethod
    def load(self, path: str) -> str:
        """
        Carga el contenido de un CSV dado un path.

        Args:
            path: Ruta del archivo. Puede ser local (file://) o remoto (s3://, gs://, etc.).

        Returns:
            Contenido del CSV como texto.
        """
        raise NotImplementedError


__all__ = ["ICsvLoader"]

