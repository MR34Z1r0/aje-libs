"""
Factory para crear servicios de monitoreo (OCP)
"""
from typing import Dict, Type, Optional
from ..contracts.monitoring import IMonitor, IEventLogger, INotificationService
from ..contracts.logging import ILogger
from ..services.monitoring import MonitorService, EventLoggerService, NotificationService
from ..exceptions import ConfigurationException


class MonitorFactory:
    """Factory para crear servicios de monitoreo (OCP - extensible sin modificar)"""
    
    _monitor_types: Dict[str, Type[IMonitor]] = {
        'dynamodb': MonitorService,
        'default': MonitorService,
    }
    
    @classmethod
    def create(
        cls,
        monitor_type: str = 'dynamodb',
        event_logger: Optional[IEventLogger] = None,
        notification_service: Optional[INotificationService] = None,
        logger: Optional[ILogger] = None,
        **config
    ) -> IMonitor:
        """
        Crea servicio de monitoreo
        
        Args:
            monitor_type: Tipo de monitor ('dynamodb', 'default')
            event_logger: Servicio de registro de eventos (opcional, se crea si no se proporciona)
            notification_service: Servicio de notificaciones (opcional)
            logger: Logger para logs internos (opcional)
            **config: Configuración adicional:
                - table_name: Nombre de la tabla DynamoDB para logs
                - project_name: Nombre del proyecto
                - team: Nombre del equipo
                - data_source: Fuente de datos
                - endpoint_name: Nombre del endpoint
                - environment: Ambiente
                - sns_topic_arn: ARN del topic SNS
                - process_guid: GUID del proceso
                - region: Región AWS (default: us-east-1)
            
        Returns:
            Instancia de IMonitor
        """
        monitor_type_lower = monitor_type.lower()
        
        if monitor_type_lower not in cls._monitor_types:
            available = ', '.join(cls._monitor_types.keys())
            raise ConfigurationException(
                f"Tipo de monitor no soportado '{monitor_type}'. Disponibles: {available}"
            )
        
        # Si no se proporciona event_logger, crear uno usando DynamoDBLogStorage
        if event_logger is None:
            # Intentar importar la implementación específica de extract_data
            try:
                from ...extract_data.services.monitoring.extract_data_event_logger_service import ExtractDataEventLoggerService
                from ...extract_data.services.log_storage.dynamodb_log_storage import DynamoDBLogStorage
                
                # Crear DynamoDBLogStorage
                table_name = config.get('table_name')
                region = config.get('region', 'us-east-1')
                
                if table_name:
                    log_storage = DynamoDBLogStorage(table_name=table_name, region=region)
                    
                    # Crear ExtractDataEventLoggerService
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
                else:
                    # Fallback a EventLoggerService básico si no hay table_name
                    event_logger = EventLoggerService(log_storage=None, logger=logger)
            except ImportError:
                # Si no se puede importar, usar EventLoggerService básico
                event_logger = EventLoggerService(log_storage=None, logger=logger)
        
        # Si no se proporciona notification_service pero hay config de SNS, crear uno
        if notification_service is None and config.get('sns_topic_arn'):
            notification_service = NotificationService(
                sns_topic_arn=config.get('sns_topic_arn'),
                logger=logger
            )
        
        monitor_class = cls._monitor_types[monitor_type_lower]
        return monitor_class(
            event_logger=event_logger,
            notification_service=notification_service,
            logger=logger
        )
    
    @classmethod
    def register_monitor(cls, monitor_type: str, monitor_class: Type[IMonitor]):
        """Registra un nuevo tipo de monitor (OCP - extensible)"""
        cls._monitor_types[monitor_type.lower()] = monitor_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Obtiene lista de tipos de monitor soportados"""
        return list(cls._monitor_types.keys())

