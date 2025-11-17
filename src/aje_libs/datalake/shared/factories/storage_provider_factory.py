# -*- coding: utf-8 -*-
"""
Factory para crear proveedores de almacenamiento (DIP - Dependency Inversion)
"""
from typing import Dict, Type, Optional
from ..contracts.storage import IStorageProvider
from ..services.storage import S3StorageProvider
from ..exceptions import ConfigurationException


class StorageProviderFactory:
    """Factory para crear proveedores de almacenamiento (OCP - extensible, DIP - retorna interfaces)"""
    
    _providers: Dict[str, Type[IStorageProvider]] = {
        's3': S3StorageProvider,
        'aws_s3': S3StorageProvider,  # Alias
        # Se pueden agregar más providers sin modificar esta clase:
        # 'azure_blob': AzureBlobStorageProvider,
        # 'gcs': GCSStorageProvider,
        # 'local': LocalStorageProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: str = 's3',
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        logger_name: Optional[str] = None,
        **kwargs
    ) -> IStorageProvider:
        """
        Crea un proveedor de almacenamiento según el tipo especificado
        
        Args:
            provider_type: Tipo de proveedor ('s3', 'azure_blob', 'gcs', etc.)
            bucket_name: Nombre del bucket/contenedor (requerido para algunos providers)
            region: Región de AWS (opcional, solo para AWS providers)
            logger_name: Nombre del logger (opcional)
            **kwargs: Configuración adicional específica del provider
            
        Returns:
            Instancia de IStorageProvider configurada
            
        Raises:
            ConfigurationException: Si el tipo de proveedor no es soportado o faltan parámetros
        """
        provider_type_lower = provider_type.lower()
        
        provider_class = cls._providers.get(provider_type_lower)
        if not provider_class:
            available = ', '.join(cls._providers.keys())
            raise ConfigurationException(
                f"Tipo de proveedor de almacenamiento no soportado '{provider_type}'. "
                f"Disponibles: {available}"
            )
        
        # Construir argumentos para el provider
        provider_kwargs = {
            'logger_name': logger_name,
            **kwargs
        }
        
        # Agregar parámetros específicos según el provider
        if provider_type_lower in ['s3', 'aws_s3']:
            if not bucket_name:
                raise ConfigurationException("bucket_name es requerido para proveedor S3")
            provider_kwargs['bucket_name'] = bucket_name
            if region:
                provider_kwargs['region'] = region
        
        return provider_class(**provider_kwargs)
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[IStorageProvider]):
        """
        Registra un nuevo tipo de proveedor de almacenamiento (OCP - extensión sin modificar)
        
        Args:
            provider_type: Nombre del tipo de proveedor
            provider_class: Clase que implementa IStorageProvider
        """
        cls._providers[provider_type.lower()] = provider_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de proveedores soportados"""
        return list(cls._providers.keys())

