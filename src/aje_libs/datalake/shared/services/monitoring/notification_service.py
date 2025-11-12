"""
Servicio de notificaciones - Implementa INotificationService (SRP)
"""
from typing import Optional

from ...contracts.monitoring import INotificationService
from ...contracts.logging import ILogger


class NotificationService(INotificationService):
    """
    Servicio de notificaciones que implementa INotificationService (SRP)
    Maneja envío de notificaciones SNS
    """
    
    def __init__(
        self,
        sns_topic_arn: Optional[str] = None,
        logger: Optional[ILogger] = None
    ):
        """
        Inicializa el servicio de notificaciones
        
        Args:
            sns_topic_arn: ARN del topic SNS para notificaciones
            logger: Logger para logs internos (DIP, opcional)
        """
        self.sns_topic_arn = sns_topic_arn
        self.logger = logger
        
        if sns_topic_arn:
            try:
                import boto3
                self.sns_client = boto3.client('sns')
            except ImportError:
                self.sns_client = None
                if logger:
                    logger.warning("boto3 no disponible, notificaciones SNS deshabilitadas")
        else:
            self.sns_client = None
    
    def send_notification(self, message: str, subject: Optional[str] = None, is_error: bool = False) -> bool:
        """Envía notificación"""
        if not self.sns_client or not self.sns_topic_arn:
            if self.logger:
                self.logger.warning("SNS no configurado, notificación no enviada")
            return False
        
        try:
            subject_prefix = "🚨 [ERROR]" if is_error else "ℹ️ [INFO]"
            final_subject = subject or f"{subject_prefix} DataLake Notification"
            
            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=final_subject,
                Message=message
            )
            
            if self.logger:
                self.logger.info("Notificación SNS enviada exitosamente")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error enviando notificación SNS: {e}")
            return False
    
    def send_error_notification(self, error_message: str, context: Optional[dict] = None) -> bool:
        """Envía notificación de error"""
        context_str = ""
        if context:
            context_str = "\n\n📊 CONTEXTO:\n"
            for key, value in list(context.items())[:10]:  # Limitar a 10 items
                context_str += f"- {key}: {value}\n"
        
        message = f"""
🚨 PROCESO FALLIDO EN DATA PIPELINE

❌ ERROR:
{error_message[:800]}
{context_str}

📋 ACCIONES:
1. Consulta logs completos en DynamoDB
2. Revisa CloudWatch logs para más detalles
3. Verifica la configuración y conexiones
        """
        
        return self.send_notification(message, is_error=True)

