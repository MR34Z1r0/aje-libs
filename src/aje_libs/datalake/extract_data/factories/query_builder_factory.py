# -*- coding: utf-8 -*-
"""
Factory para crear Query Builders específicos por tipo de base de datos.
"""
from typing import Optional
from ..contracts.query_builder_interface import IQueryBuilder  # ✅ Corregido: ..contracts (no ...contracts)
from ..services.query_builders.sql_server_query_builder import SQLServerQueryBuilder
from ..services.query_builders.postgresql_query_builder import PostgreSQLQueryBuilder
from ...shared.models import TableConfig
from ...shared.services.logging import LoggerService

logger = LoggerService.get_logger(__name__)


class QueryBuilderFactory:
    """Factory para crear Query Builders según el tipo de base de datos"""
    
    # Mapeo de tipos de DB a sus Query Builders
    _BUILDERS = {
        'sqlserver': SQLServerQueryBuilder,
        'mssql': SQLServerQueryBuilder,
        'postgresql': PostgreSQLQueryBuilder,
        'postgres': PostgreSQLQueryBuilder,
    }
    
    @classmethod
    def create(
        cls,
        db_type: str,
        table_config: TableConfig,
        logger_name: Optional[str] = None
    ) -> IQueryBuilder:
        """
        Crea un Query Builder apropiado para el tipo de base de datos.
        
        Args:
            db_type: Tipo de base de datos ('sqlserver', 'postgresql', etc.)
            table_config: Configuración de la tabla
            logger_name: Nombre del logger (opcional)
            
        Returns:
            Instancia de IQueryBuilder apropiada para el tipo de DB
            
        Raises:
            ValueError: Si el tipo de DB no está soportado
        """
        db_type_lower = db_type.lower().strip()
        
        builder_class = cls._BUILDERS.get(db_type_lower)
        
        if not builder_class:
            supported = ', '.join(cls._BUILDERS.keys())
            error_msg = (
                f"Tipo de base de datos '{db_type}' no está soportado. "
                f"Tipos soportados: {supported}"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.debug(f"✅ Creando QueryBuilder: {builder_class.__name__} para DB tipo: {db_type_lower}")
        
        return builder_class(table_config)
    
    @classmethod
    def get_supported_db_types(cls) -> list:
        """Retorna lista de tipos de base de datos soportados"""
        return list(cls._BUILDERS.keys())
    
    @classmethod
    def register_builder(cls, db_type: str, builder_class: type):
        """
        Registra un nuevo Query Builder para un tipo de DB.
        
        Args:
            db_type: Tipo de base de datos (ej: 'mysql', 'oracle')
            builder_class: Clase que implementa IQueryBuilder
        """
        if not issubclass(builder_class, IQueryBuilder):
            raise ValueError(f"{builder_class.__name__} debe implementar IQueryBuilder")
        
        cls._BUILDERS[db_type.lower()] = builder_class
        logger.info(f"✅ QueryBuilder registrado: {builder_class.__name__} para DB tipo: {db_type}")

