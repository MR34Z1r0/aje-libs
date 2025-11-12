"""
Factory para crear servicios de watermark (OCP)
"""
from typing import Dict, Type, Optional
from ..contracts.watermark import IWatermarkStorage, IWatermarkManager
from ..contracts.logging import ILogger
from ..exceptions import ConfigurationException


class WatermarkFactory:
    """Factory para crear servicios de watermark (OCP - extensible sin modificar)"""
    
    _storage_types: Dict[str, Type[IWatermarkStorage]] = {
        # Se registrarán cuando migremos los servicios de watermark
        # 'dynamodb': DynamoDBWatermarkStorageService,
        # 'csv': CSVWatermarkStorageService,
    }
    
    @classmethod
    def create(
        cls,
        storage_type: str = 'dynamodb',
        enable_transactions: bool = True,
        logger: Optional[ILogger] = None,
        **config
    ) -> IWatermarkStorage:
        """
        Crea servicio de almacenamiento de watermarks
        
        Args:
            storage_type: Tipo de almacenamiento ('dynamodb', 'csv')
            enable_transactions: Si True, envuelve en capa transaccional
            logger: Logger para logs internos (opcional)
            **config: Configuración específica (table_name, csv_file_path, etc.)
            
        Returns:
            Instancia de IWatermarkStorage
        """
        storage_type_lower = storage_type.lower()
        
        if storage_type_lower not in cls._storage_types:
            available = ', '.join(cls._storage_types.keys()) if cls._storage_types else 'ninguno'
            raise ConfigurationException(
                f"Tipo de almacenamiento de watermark no soportado '{storage_type}'. "
                f"Disponibles: {available}. "
                f"Nota: Los servicios de watermark aún no han sido migrados completamente."
            )
        
        storage_class = cls._storage_types[storage_type_lower]
        
        # Crear instancia base
        base_storage = storage_class(**config)
        
        # Envolver en capa transaccional si está habilitado
        if enable_transactions:
            # Nota: TransactionalWatermarkStorage se migrará después
            # Por ahora retornamos el storage base
            if logger:
                logger.info("Transactional watermark storage habilitado (pendiente de migración)")
            return base_storage
        else:
            return base_storage
    
    @classmethod
    def register_storage(cls, storage_type: str, storage_class: Type[IWatermarkStorage]):
        """Registra un nuevo tipo de almacenamiento (OCP - extensible)"""
        cls._storage_types[storage_type.lower()] = storage_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de almacenamiento soportados"""
        return list(cls._storage_types.keys())

