# -*- coding: utf-8 -*-
"""
Factory de componentes para light transform (DIP - Dependency Inversion)
Implementa ILightTransformComponentFactory para inyección de dependencias
"""
from typing import Optional
from ..contracts.factories.component_factory_interface import ILightTransformComponentFactory
from ..models import LightTransformConfig
from ..contracts.data_processing import ILightTransformProcessor
from ...shared.contracts.monitoring import IMonitor
from ...shared.factories import MonitorFactory
from ...shared.services.logging import LoggerService
from .processor_factory import LightTransformProcessorFactory


class DefaultLightTransformComponentFactory(ILightTransformComponentFactory):
    """Factory por defecto para crear componentes de light transform (DIP - implementa ILightTransformComponentFactory)"""
    
    def __init__(self, logger_name: Optional[str] = None):
        """
        Inicializa el factory
        
        Args:
            logger_name: Nombre del logger (opcional)
        """
        self.logger = LoggerService.get_logger(logger_name or __name__)
    
    def create_processor(
        self, 
        config: LightTransformConfig, 
        spark, 
        s3_client=None
    ) -> ILightTransformProcessor:
        """Crea un procesador según la configuración"""
        self.logger.debug(f"Creando processor para {config.table_name}")
        
        processor_factory = LightTransformProcessorFactory(
            spark=spark,
            s3_client=s3_client,
            logger=self.logger,
            config_source_type=config.config_source_type,
            data_loader_type=config.data_loader_type,
            data_writer_type=config.data_writer_type,
        )
        
        return processor_factory.create()
    
    def create_monitor(
        self, 
        config: LightTransformConfig, 
        process_guid: Optional[str] = None
    ) -> Optional[IMonitor]:
        """Crea un monitor según la configuración"""
        if not config.log_storage:
            return None
        
        self.logger.debug(f"Creando monitor: {config.monitor_type}")
        
        # Extraer table_name de log_storage
        table_name = None
        if config.log_storage and config.log_storage.provider == 'dynamodb':
            table_name = config.log_storage.location
        
        # Extraer notification ARNs
        notification_arn = None
        sns_topic_arns = {}
        if config.notification_targets:
            for event_type, target in config.notification_targets.items():
                if target and target.provider == 'sns' and target.location:
                    sns_topic_arns[event_type] = target.location
            notification_arn = sns_topic_arns.get('failed')
        elif config.notification_target and config.notification_target.provider == 'sns':
            notification_arn = config.notification_target.location
            sns_topic_arns['failed'] = notification_arn
        
        monitor_config = {
            'table_name': table_name,
            'team': config.team,
            'data_source': config.data_source,
            'endpoint_name': config.endpoint_name,
            'environment': config.environment,
            'sns_topic_arn': notification_arn,
            'sns_topic_arns': sns_topic_arns if sns_topic_arns else None,
            'process_guid': process_guid,
            'flow_name': 'light_transform',
            'event_logger_type': 'light_transform',
            'notification_provider': 'sns',
        }
        
        # Añadir región si está disponible
        if hasattr(config.log_storage, 'options') and config.log_storage.options and config.log_storage.options.get('region'):
            monitor_config['region'] = config.log_storage.options['region']
        
        return MonitorFactory.create(
            monitor_type=config.monitor_type,
            logger=self.logger,
            **monitor_config
        )

