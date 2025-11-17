"""
Factory para crear servicios de monitoreo (OCP - refactorizado para usar builders)
"""
from typing import Dict, Type, Optional
from ..contracts.monitoring import IMonitor, IEventLogger, INotificationService
from ..contracts.logging import ILogger
from ..services.monitoring import MonitorService
from ..exceptions import ConfigurationException
from .event_logger_builder import EventLoggerBuilder
from .notification_service_builder import NotificationServiceBuilder


class MonitorFactory:
    """Factory para crear servicios de monitoreo (OCP - extensible sin modificar, SRP - usa builders)"""
    
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
        Crea servicio de monitoreo usando builders internos (SRP - delegación de responsabilidades)
        
        Args:
            monitor_type: Tipo de monitor ('dynamodb', 'default')
            event_logger: Servicio de registro de eventos (opcional, se crea si no se proporciona)
            notification_service: Servicio de notificaciones (opcional)
            logger: Logger para logs internos (opcional)
            **config: Configuración adicional:
                - event_logger_type: Tipo de event logger ('default', 'extract_data', 'light_transform')
                - notification_provider: Proveedor de notificaciones ('sns', etc.)
                - table_name: Nombre de la tabla DynamoDB para logs
                - project_name: Nombre del proyecto
                - team: Nombre del equipo
                - data_source: Fuente de datos
                - endpoint_name: Nombre del endpoint
                - environment: Ambiente
                - sns_topic_arn: ARN del topic SNS
                - sns_topic_arns: Dict con ARNs por tipo de evento
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
        
        # ✅ Usar EventLoggerBuilder para crear event_logger (SRP - separación de responsabilidades)
        if event_logger is None:
            event_logger_type = config.get('event_logger_type', 'default')
            # Extraer argumentos específicos de config para evitar duplicados
            event_logger_config = {
                k: v for k, v in config.items()
                if k not in ['event_logger_type']
            }
            
            event_logger = EventLoggerBuilder.build(
                event_logger_type=event_logger_type,
                logger=logger,
                **event_logger_config
            )
        
        # ✅ Usar NotificationServiceBuilder para crear notification_service (SRP)
        if notification_service is None:
            # Extraer argumentos específicos de config para evitar duplicados
            notification_config = {
                k: v for k, v in config.items()
                if k not in ['sns_topic_arn', 'sns_topic_arns', 'notification_provider']
            }
            
            notification_service = NotificationServiceBuilder.build(
                notification_provider=config.get('notification_provider', 'sns'),
                sns_topic_arn=config.get('sns_topic_arn'),
                sns_topic_arns=config.get('sns_topic_arns'),
                logger=logger,
                **notification_config
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

