# -*- coding: utf-8 -*-
"""
Factory para crear proveedores de secretos (DIP - Dependency Inversion)
"""
from typing import Dict, Type, Optional
from ..contracts.secrets import ISecretProvider
from ..services.secrets import AWSSecretsProvider
from ..exceptions import ConfigurationException


class SecretProviderFactory:
    """Factory para crear proveedores de secretos (OCP - extensible, DIP - retorna interfaces)"""
    
    _providers: Dict[str, Type[ISecretProvider]] = {
        'aws_secrets_manager': AWSSecretsProvider,
        'aws_secrets': AWSSecretsProvider,  # Alias
        'secrets_manager': AWSSecretsProvider,  # Alias
        # Se pueden agregar más providers sin modificar esta clase:
        # 'vault': HashiCorpVaultProvider,
        # 'azure_key_vault': AzureKeyVaultProvider,
        # 'env': EnvironmentSecretProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: str = 'aws_secrets_manager',
        region: Optional[str] = None,
        logger_name: Optional[str] = None,
        **kwargs
    ) -> ISecretProvider:
        """
        Crea un proveedor de secretos según el tipo especificado
        
        Args:
            provider_type: Tipo de proveedor ('aws_secrets_manager', 'vault', etc.)
            region: Región de AWS (opcional, solo para AWS providers)
            logger_name: Nombre del logger (opcional)
            **kwargs: Configuración adicional específica del provider
            
        Returns:
            Instancia de ISecretProvider configurada
            
        Raises:
            ConfigurationException: Si el tipo de proveedor no es soportado
        """
        provider_type_lower = provider_type.lower()
        
        provider_class = cls._providers.get(provider_type_lower)
        if not provider_class:
            available = ', '.join(cls._providers.keys())
            raise ConfigurationException(
                f"Tipo de proveedor de secretos no soportado '{provider_type}'. "
                f"Disponibles: {available}"
            )
        
        # Construir argumentos para el provider
        provider_kwargs = {
            'logger_name': logger_name,
            **kwargs
        }
        
        # Agregar región si está disponible y el provider la necesita
        if region:
            provider_kwargs['region'] = region
        
        return provider_class(**provider_kwargs)
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[ISecretProvider]):
        """
        Registra un nuevo tipo de proveedor de secretos (OCP - extensión sin modificar)
        
        Args:
            provider_type: Nombre del tipo de proveedor
            provider_class: Clase que implementa ISecretProvider
        """
        cls._providers[provider_type.lower()] = provider_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de proveedores soportados"""
        return list(cls._providers.keys())

