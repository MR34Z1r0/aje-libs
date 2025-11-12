"""
Servicio de registro de eventos - Implementa IEventLogger (SRP)
"""
from typing import Dict, Any, Optional

from ...contracts.monitoring import IEventLogger
from ...contracts.logging import ILogger


class EventLoggerService(IEventLogger):
    """
    Servicio de registro de eventos que implementa IEventLogger (SRP)
    Maneja el almacenamiento de eventos en DynamoDB
    """
    
    def __init__(
        self,
        log_storage,  # ILogStorage - se importará después de crear el servicio
        logger: Optional[ILogger] = None
    ):
        """
        Inicializa el servicio de registro de eventos
        
        Args:
            log_storage: Servicio de almacenamiento de logs (DIP)
            logger: Logger para logs internos (DIP, opcional)
        """
        self.log_storage = log_storage
        self.logger = logger
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Registra un evento"""
        try:
            log_entry = {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": event_data.get("timestamp")
            }
            return self.log_storage.store_log(log_entry)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error registrando evento: {e}")
            return False
    
    def log_process_status(
        self,
        status: str,
        message: str,
        table_name: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra estado de proceso"""
        # Esta implementación será completada cuando migremos DynamoDBLogger
        # Por ahora retornamos un placeholder
        if self.logger:
            self.logger.info(f"Registrando estado: {status} - {table_name}")
        return ""

