# -*- coding: utf-8 -*-
"""
Factory para crear proveedores de bases de datos NoSQL (DIP - Dependency Inversion)
"""
from typing import Dict, Type, Optional
from ..contracts.data_access import IDatabaseProvider
from ..services.data_access import DynamoDBProvider
from ..exceptions import ConfigurationException


class DatabaseProviderFactory:
    """Factory para crear proveedores de bases de datos NoSQL (OCP - extensible, DIP - retorna interfaces)"""
    
    _providers: Dict[str, Type[IDatabaseProvider]] = {
        'dynamodb': DynamoDBProvider,
        'aws_dynamodb': DynamoDBProvider,  # Alias
        # Se pueden agregar más providers sin modificar esta clase:
        # 'mongodb': MongoDBProvider,
        # 'cassandra': CassandraProvider,
        # 'cosmosdb': CosmosDBProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: str = 'dynamodb',
        table_name: Optional[str] = None,
        pk_name: Optional[str] = None,
        sk_name: Optional[str] = None,
        region: Optional[str] = None,
        logger_name: Optional[str] = None,
        **kwargs
    ) -> IDatabaseProvider:
        """
        Crea un proveedor de base de datos según el tipo especificado
        
        Args:
            provider_type: Tipo de proveedor ('dynamodb', 'mongodb', etc.)
            table_name: Nombre de la tabla/colección (requerido para algunos providers)
            pk_name: Nombre de la clave de partición (requerido para algunos providers)
            sk_name: Nombre de la clave de ordenamiento (opcional)
            region: Región de AWS (opcional, solo para AWS providers)
            logger_name: Nombre del logger (opcional)
            **kwargs: Configuración adicional específica del provider
            
        Returns:
            Instancia de IDatabaseProvider configurada
            
        Raises:
            ConfigurationException: Si el tipo de proveedor no es soportado o faltan parámetros
        """
        provider_type_lower = provider_type.lower()
        
        provider_class = cls._providers.get(provider_type_lower)
        if not provider_class:
            available = ', '.join(cls._providers.keys())
            raise ConfigurationException(
                f"Tipo de proveedor de base de datos no soportado '{provider_type}'. "
                f"Disponibles: {available}"
            )
        
        # Construir argumentos para el provider
        provider_kwargs = {
            'logger_name': logger_name,
            **kwargs
        }
        
        # Agregar parámetros específicos según el provider
        if provider_type_lower in ['dynamodb', 'aws_dynamodb']:
            if not table_name:
                raise ConfigurationException("table_name es requerido para proveedor DynamoDB")
            if not pk_name:
                raise ConfigurationException("pk_name es requerido para proveedor DynamoDB")
            provider_kwargs['table_name'] = table_name
            provider_kwargs['pk_name'] = pk_name
            if sk_name:
                provider_kwargs['sk_name'] = sk_name
            if region:
                provider_kwargs['region'] = region
        
        return provider_class(**provider_kwargs)
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[IDatabaseProvider]):
        """
        Registra un nuevo tipo de proveedor de base de datos (OCP - extensión sin modificar)
        
        Args:
            provider_type: Nombre del tipo de proveedor
            provider_class: Clase que implementa IDatabaseProvider
        """
        cls._providers[provider_type.lower()] = provider_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de proveedores soportados"""
        return list(cls._providers.keys())

