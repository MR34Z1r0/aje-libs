"""
Servicio de monitoreo compartido - Implementa IMonitor (SRP)
"""
from typing import Dict, Any, Optional

from ...contracts.monitoring import IMonitor, IEventLogger, INotificationService
from ...contracts.logging import ILogger


class MonitorService(IMonitor):
    """
    Servicio de monitoreo que implementa IMonitor (SRP)
    Coordina EventLogger y NotificationService
    """
    
    def __init__(
        self,
        event_logger: IEventLogger,
        notification_service: Optional[INotificationService] = None,
        logger: Optional[ILogger] = None
    ):
        """
        Inicializa el servicio de monitoreo
        
        Args:
            event_logger: Servicio de registro de eventos (DIP)
            notification_service: Servicio de notificaciones (DIP, opcional)
            logger: Logger para logs internos (DIP, opcional)
        """
        self.event_logger = event_logger
        self.notification_service = notification_service
        self.logger = logger
        self._log_storage = getattr(event_logger, "log_storage", None)
    
    def log_start(self, table_name: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra inicio de proceso. Retorna process_id"""
        try:
            process_id = self.event_logger.log_process_status(
                status="RUNNING",
                message=f"Iniciando procesamiento de tabla {table_name}",
                table_name=table_name,
                job_name=job_name,
                context=metadata or {}
            )
            
            if self.logger:
                self.logger.info(f"Inicio de proceso registrado: {process_id}", {"table": table_name})
            
            return process_id
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al registrar inicio: {e}")
            return ""
    
    def log_success(self, table_name: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra éxito de proceso. Retorna process_id"""
        try:
            process_id = self.event_logger.log_process_status(
                status="SUCCESS",
                message=f"Procesamiento exitoso de tabla {table_name}",
                table_name=table_name,
                job_name=job_name,
                context=metadata or {}
            )
            
            if self.logger:
                self.logger.info(f"Éxito de proceso registrado: {process_id}", {"table": table_name})
            
            return process_id
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al registrar éxito: {e}")
            return ""
    
    def log_error(self, table_name: str, error_message: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra error de proceso. Retorna process_id"""
        try:
            error_metadata = metadata or {}
            error_metadata['error_message'] = error_message
            
            process_id = self.event_logger.log_process_status(
                status="FAILED",
                message=f"Error procesando tabla {table_name}: {error_message}",
                table_name=table_name,
                job_name=job_name,
                context=error_metadata
            )
            
            # Enviar notificación si está disponible
            if self.notification_service:
                self.notification_service.send_error_notification(
                    error_message=error_message,
                    context={"table_name": table_name, "job_name": job_name, **error_metadata}
                )
            
            if self.logger:
                self.logger.error(f"Error de proceso registrado: {process_id}", {"table": table_name, "error": error_message[:200]})
            
            return process_id
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al registrar fallo: {e}")
            return ""
    
    def log_warning(self, table_name: str, warning_message: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra advertencia de proceso. Retorna process_id"""
        try:
            warning_metadata = metadata or {}
            warning_metadata['warning_message'] = warning_message
            
            process_id = self.event_logger.log_process_status(
                status="WARNING",
                message=f"Advertencia procesando tabla {table_name}: {warning_message}",
                table_name=table_name,
                job_name=job_name,
                context=warning_metadata
            )
            
            if self.logger:
                self.logger.warning(f"Advertencia de proceso registrada: {process_id}", {"table": table_name, "warning": warning_message[:200]})
            
            return process_id
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al registrar warning: {e}")
            return ""
    
    def cleanup_table_logs(self, table_name: str) -> Dict[str, Any]:
        """Limpia los logs asociados a una tabla en DynamoDB."""
        log_storage = self._log_storage
        if log_storage and hasattr(log_storage, 'cleanup_table_logs'):
            team = getattr(self.event_logger, 'team', '')
            data_source = getattr(self.event_logger, 'data_source', '')
            endpoint_name = getattr(self.event_logger, 'endpoint_name', '')
            if self.logger:
                self.logger.info(
                    "Iniciando limpieza de logs en DynamoDB",
                    {
                        "table": table_name,
                        "team": team,
                        "data_source": data_source,
                        "endpoint": endpoint_name,
                    }
                )
            return log_storage.cleanup_table_logs(
                table_name=table_name,
                team=team,
                data_source=data_source,
                endpoint_name=endpoint_name,
            )
        if hasattr(self.event_logger, 'cleanup_table_logs'):
            return self.event_logger.cleanup_table_logs(table_name)
        raise NotImplementedError("El monitor actual no soporta cleanup_table_logs")

