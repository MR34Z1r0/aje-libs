# -*- coding: utf-8 -*-
"""
Builder para crear Event Loggers (SRP - Single Responsibility)
"""
from typing import Dict, Type, Optional, Any
from ..contracts.monitoring import IEventLogger
from ..contracts.logging import ILogger
from ..exceptions import ConfigurationException


class EventLoggerBuilder:
    """Builder para crear servicios de registro de eventos (OCP - extensible sin modificar)"""
    
    _event_logger_types: Dict[str, Type[IEventLogger]] = {}
    
    @classmethod
    def build(
        cls,
        event_logger_type: str = 'default',
        logger: Optional[ILogger] = None,
        **config
    ) -> IEventLogger:
        """
        Construye un Event Logger según el tipo especificado
        
        Args:
            event_logger_type: Tipo de event logger ('default', 'extract_data', 'light_transform')
            logger: Logger para logs internos (opcional)
            **config: Configuración adicional:
                - table_name: Nombre de la tabla DynamoDB para logs
                - region: Región AWS
                - team: Nombre del equipo
                - data_source: Fuente de datos
                - endpoint_name: Nombre del endpoint
                - flow_name: Nombre del flujo
                - environment: Ambiente
                - process_guid: GUID del proceso
                
        Returns:
            Instancia de IEventLogger configurada
        """
        event_logger_type_lower = event_logger_type.lower()
        
        if event_logger_type_lower not in cls._event_logger_types:
            # Si no está registrado, intentar importar por defecto
            if event_logger_type_lower == 'extract_data':
                try:
                    from ...extract_data.services.monitoring.extract_data_event_logger_service import ExtractDataEventLoggerService
                    from ...extract_data.services.log_storage.dynamodb_log_storage import DynamoDBLogStorage
                    
                    table_name = config.get('table_name')
                    region = config.get('region', 'us-east-1')
                    
                    if table_name:
                        log_storage = DynamoDBLogStorage(table_name=table_name, region=region)
                        event_logger = ExtractDataEventLoggerService(
                            log_storage=log_storage,
                            team=config.get('team', ''),
                            data_source=config.get('data_source', ''),
                            endpoint_name=config.get('endpoint_name', ''),
                            flow_name=config.get('flow_name', 'extract_data'),
                            environment=config.get('environment', ''),
                            logger=logger,
                            process_guid=config.get('process_guid')
                        )
                        return event_logger
                except ImportError:
                    pass
            
            # Fallback a EventLoggerService básico
            from ..services.monitoring.event_logger_service import EventLoggerService
            return EventLoggerService(log_storage=None, logger=logger)
        
        event_logger_class = cls._event_logger_types[event_logger_type_lower]
        
        # Construir según el tipo
        if event_logger_type_lower == 'extract_data':
            from ...extract_data.services.log_storage.dynamodb_log_storage import DynamoDBLogStorage
            
            table_name = config.get('table_name')
            region = config.get('region', 'us-east-1')
            
            if table_name:
                log_storage = DynamoDBLogStorage(table_name=table_name, region=region)
                return event_logger_class(
                    log_storage=log_storage,
                    team=config.get('team', ''),
                    data_source=config.get('data_source', ''),
                    endpoint_name=config.get('endpoint_name', ''),
                    flow_name=config.get('flow_name', 'extract_data'),
                    environment=config.get('environment', ''),
                    logger=logger,
                    process_guid=config.get('process_guid')
                )
        
        # Construcción genérica
        return event_logger_class(log_storage=None, logger=logger)
    
    @classmethod
    def register_event_logger(cls, event_logger_type: str, event_logger_class: Type[IEventLogger]):
        """Registra un nuevo tipo de event logger (OCP - extensible)"""
        cls._event_logger_types[event_logger_type.lower()] = event_logger_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de event logger soportados"""
        return list(cls._event_logger_types.keys())

