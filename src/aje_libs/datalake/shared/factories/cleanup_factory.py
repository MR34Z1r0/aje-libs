"""
Factory para crear servicios de limpieza (OCP)
"""
from typing import Dict, Type, List, Optional
from ..contracts.cleanup import ICleanupService, IResourceCleaner
from ..contracts.logging import ILogger
from ..services.cleanup import CleanupService, S3CleanupService, DynamoDBCleanupService
from ..exceptions import ConfigurationException


class CleanupFactory:
    """Factory para crear servicios de limpieza (OCP - extensible sin modificar)"""
    
    _cleaner_types: Dict[str, Type[IResourceCleaner]] = {
        's3': S3CleanupService,
        'dynamodb': DynamoDBCleanupService,
    }
    
    @classmethod
    def create(
        cls,
        cleanup_type: str = 's3',
        resource_cleaners: Optional[List[IResourceCleaner]] = None,
        logger: Optional[ILogger] = None,
        **config
    ) -> ICleanupService:
        """
        Crea servicio de limpieza
        
        Args:
            cleanup_type: Tipo de limpieza ('s3', 'dynamodb', 'combined')
            resource_cleaners: Lista de limpiadores específicos (opcional)
            logger: Logger para logs internos (opcional)
            **config: Configuración adicional
            
        Returns:
            Instancia de ICleanupService
        """
        cleanup_type_lower = cleanup_type.lower()
        
        # Si se proporcionan limpiadores específicos, usarlos
        if resource_cleaners:
            return CleanupService(resource_cleaners=resource_cleaners, logger=logger)
        
        # Crear limpiadores según el tipo
        cleaners = []
        
        if cleanup_type_lower == 'combined' or cleanup_type_lower == 'all':
            # Crear múltiples limpiadores
            if config.get('s3_bucket'):
                cleaners.append(S3CleanupService(logger=logger))
            if config.get('dynamodb_table'):
                cleaners.append(DynamoDBCleanupService(
                    table_name=config['dynamodb_table'],
                    logger=logger
                ))
        elif cleanup_type_lower in cls._cleaner_types:
            cleaner_class = cls._cleaner_types[cleanup_type_lower]
            
            if cleanup_type_lower == 's3':
                cleaners.append(cleaner_class(logger=logger))
            elif cleanup_type_lower == 'dynamodb':
                if not config.get('table_name'):
                    raise ConfigurationException("DynamoDBCleanupService requiere 'table_name'")
                cleaners.append(cleaner_class(
                    table_name=config['table_name'],
                    logger=logger
                ))
        else:
            available = ', '.join(['combined', 'all'] + list(cls._cleaner_types.keys()))
            raise ConfigurationException(
                f"Tipo de limpieza no soportado '{cleanup_type}'. Disponibles: {available}"
            )
        
        if not cleaners:
            raise ConfigurationException("No se pudo crear ningún limpiador de recursos")
        
        return CleanupService(resource_cleaners=cleaners, logger=logger)
    
    @classmethod
    def create_resource_cleaner(
        cls,
        cleaner_type: str,
        logger: Optional[ILogger] = None,
        **config
    ) -> IResourceCleaner:
        """
        Crea un limpiador de recursos específico
        
        Args:
            cleaner_type: Tipo de limpiador ('s3', 'dynamodb')
            logger: Logger para logs internos (opcional)
            **config: Configuración específica del limpiador
            
        Returns:
            Instancia de IResourceCleaner
        """
        cleaner_type_lower = cleaner_type.lower()
        
        if cleaner_type_lower not in cls._cleaner_types:
            available = ', '.join(cls._cleaner_types.keys())
            raise ConfigurationException(
                f"Tipo de limpiador no soportado '{cleaner_type}'. Disponibles: {available}"
            )
        
        cleaner_class = cls._cleaner_types[cleaner_type_lower]
        
        if cleaner_type_lower == 's3':
            return cleaner_class(logger=logger)
        elif cleaner_type_lower == 'dynamodb':
            if not config.get('table_name'):
                raise ConfigurationException("DynamoDBCleanupService requiere 'table_name'")
            return cleaner_class(
                table_name=config['table_name'],
                logger=logger
            )
    
    @classmethod
    def register_cleaner(cls, cleaner_type: str, cleaner_class: Type[IResourceCleaner]):
        """Registra un nuevo tipo de limpiador (OCP - extensible)"""
        cls._cleaner_types[cleaner_type.lower()] = cleaner_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de limpiador soportados"""
        return list(cls._cleaner_types.keys())

