# -*- coding: utf-8 -*-
"""
Builder para crear Notification Services (SRP - Single Responsibility)
"""
from typing import Dict, Optional
from ..contracts.monitoring import INotificationService
from ..contracts.logging import ILogger
from ..services.monitoring.notification_service import NotificationService


class NotificationServiceBuilder:
    """Builder para crear servicios de notificación (OCP - extensible sin modificar)"""
    
    @classmethod
    def build(
        cls,
        notification_provider: str = 'sns',
        sns_topic_arn: Optional[str] = None,
        sns_topic_arns: Optional[Dict[str, str]] = None,
        logger: Optional[ILogger] = None,
        **config
    ) -> Optional[INotificationService]:
        """
        Construye un Notification Service según el proveedor especificado
        
        Args:
            notification_provider: Proveedor de notificaciones ('sns', 'pubsub', etc.)
            sns_topic_arn: ARN del topic SNS (deprecated, usar sns_topic_arns)
            sns_topic_arns: Dict con ARNs por tipo de evento ('failed', 'success', 'warning')
            logger: Logger para logs internos (opcional)
            **config: Configuración adicional
            
        Returns:
            Instancia de INotificationService configurada o None si no hay ARN
        """
        notification_provider_lower = notification_provider.lower()
        
        # Actualmente solo soportamos SNS
        if notification_provider_lower == 'sns':
            # Priorizar sns_topic_arns si está disponible, sino usar sns_topic_arn
            effective_arn = None
            if sns_topic_arns:
                effective_arn = sns_topic_arns.get('failed')  # Usar 'failed' para compatibilidad
            elif sns_topic_arn:
                effective_arn = sns_topic_arn
            
            if effective_arn:
                return NotificationService(
                    sns_topic_arn=effective_arn,
                    logger=logger
                )
        
        # Futuro: soportar otros proveedores
        # elif notification_provider_lower == 'pubsub':
        #     return PubSubNotificationService(...)
        
        return None
    
    @classmethod
    def build_from_config(cls, config: dict, logger: Optional[ILogger] = None) -> Optional[INotificationService]:
        """
        Construye un Notification Service desde un diccionario de configuración
        
        Args:
            config: Diccionario con configuración:
                - notification_provider: Proveedor ('sns', etc.)
                - sns_topic_arn: ARN del topic (opcional)
                - sns_topic_arns: Dict con ARNs por tipo (opcional)
            logger: Logger para logs internos (opcional)
            
        Returns:
            Instancia de INotificationService configurada o None
        """
        return cls.build(
            notification_provider=config.get('notification_provider', 'sns'),
            sns_topic_arn=config.get('sns_topic_arn'),
            sns_topic_arns=config.get('sns_topic_arns'),
            logger=logger,
            **{k: v for k, v in config.items() if k not in ['notification_provider', 'sns_topic_arn', 'sns_topic_arns']}
        )

