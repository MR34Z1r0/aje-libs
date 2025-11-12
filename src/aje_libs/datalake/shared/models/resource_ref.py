"""Referencia genérica a recursos externos (storage, configuraciones, etc.)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ResourceRef:
    """Describe el proveedor y ubicación de un recurso configurable."""

    provider: str
    location: str
    options: Dict[str, Any] = field(default_factory=dict)



