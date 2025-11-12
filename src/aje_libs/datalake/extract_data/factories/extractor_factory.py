# -*- coding: utf-8 -*-
from typing import Dict, Type
from ..contracts.extractor_interface import IExtractor
from ..models.database_config import DatabaseConfig
from ..services.extractors.sql_server_extractor import SQLServerExtractor
from aje_libs.datalake.shared.exceptions import ConfigurationException as ConfigurationError

class ExtractorFactory:
    """Factory to create appropriate extractor instances"""
    
    _extractors: Dict[str, Type[IExtractor]] = {
        'sqlserver': SQLServerExtractor,
        'mssql': SQLServerExtractor,
        # Add more extractors here as they are implemented
        # 'postgresql': PostgreSQLExtractor,
        # 'oracle': OracleExtractor,
        # 'mysql': MySQLExtractor,
    }
    
    @classmethod
    def create(cls, db_type: str, config: DatabaseConfig, name_logger: str = None) -> IExtractor:
        """
        Create appropriate extractor based on database type
        
        Args:
            db_type: Type of database ('sqlserver', 'postgresql', etc.)
            config: Database configuration
            name_logger: Logger name to use for unified logging
            
        Returns:
            Configured extractor instance
            
        Raises:
            ConfigurationError: If database type is not supported
        """
        db_type_lower = db_type.lower()
        
        if db_type_lower not in cls._extractors:
            available_types = ', '.join(cls._extractors.keys())
            raise ConfigurationError(
                f"Unsupported database type '{db_type}'. "
                f"Available types: {available_types}"
            )
        
        extractor_class = cls._extractors[db_type_lower]
        # Pass name_logger if supported by the extractor
        try:
            return extractor_class(config, name_logger=name_logger)
        except TypeError:
            # Fallback for extractors that do not accept name_logger
            return extractor_class(config)
    
    @classmethod
    def register_extractor(cls, db_type: str, extractor_class: Type[IExtractor]):
        """Register a new extractor type"""
        cls._extractors[db_type.lower()] = extractor_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Get list of supported database types"""
        return list(cls._extractors.keys())