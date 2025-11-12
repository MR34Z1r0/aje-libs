"""Modelo reutilizable para describir endpoints de origen/destino."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EndpointConfig:
    endpoint_name: str
    environment: Optional[str] = None
    src_db_name: Optional[str] = None
    src_server_name: Optional[str] = None
    src_db_username: Optional[str] = None


