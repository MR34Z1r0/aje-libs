"""Referencia genérica a recursos externos (storage, configuraciones, etc.)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import re


@dataclass(frozen=True)
class ResourceRef:
    """
    Describe el proveedor y ubicación de un recurso configurable.
    
    Attributes:
        provider: Proveedor del recurso (s3, sns, dynamodb, csv, http, etc.).
        location: Ubicación del recurso (ARN, URL, ruta, etc.).
        options: Opciones adicionales específicas del proveedor.
        
    Example:
        >>> s3_ref = ResourceRef(
        ...     provider="s3",
        ...     location="s3://bucket/path/to/file.parquet",
        ...     options={"region": "us-east-1"}
        ... )
    """
    
    provider: str
    location: str
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Valida que provider y location sean válidos"""
        # Validar provider
        valid_providers = [
            's3', 'sns', 'dynamodb', 'sqs', 'csv', 'http', 'https',
            'gcs', 'azure_blob', 'pubsub',  # Futuros providers
        ]
        provider_lower = self.provider.lower()
        
        if provider_lower not in valid_providers:
            raise ValueError(
                f"Provider '{self.provider}' no es válido. "
                f"Disponibles: {', '.join(valid_providers)}"
            )
        
        # Validar location
        if not self.location or not self.location.strip():
            raise ValueError("Location no puede estar vacío")
        
        # Validación específica por provider
        location_lower = self.location.lower().strip()
        
        if provider_lower == 's3' and not location_lower.startswith('s3://'):
            # Permitir solo el nombre del bucket (se convertirá a s3://)
            if not re.match(r'^[a-z0-9][a-z0-9\-\.]*[a-z0-9]$', location_lower):
                raise ValueError(
                    f"S3 location debe empezar con 's3://' o ser un nombre de bucket válido. "
                    f"Recibido: '{self.location}'"
                )
        
        elif provider_lower in ['http', 'https']:
            if not location_lower.startswith(('http://', 'https://')):
                raise ValueError(
                    f"{provider_lower.upper()} location debe empezar con 'http://' o 'https://'. "
                    f"Recibido: '{self.location}'"
                )
        
        elif provider_lower == 'csv':
            # CSV puede ser ruta local o S3
            if not (location_lower.startswith('s3://') or 
                    location_lower.endswith('.csv') or 
                    '/' in location_lower):
                raise ValueError(
                    f"CSV location debe ser una ruta válida o URL S3. "
                    f"Recibido: '{self.location}'"
                )
        
        # Validar que options sea un diccionario
        if not isinstance(self.options, dict):
            raise TypeError(f"Options debe ser un diccionario, recibido: {type(self.options)}")



