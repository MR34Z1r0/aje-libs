"""
Interface para servicios de notificación (ISP)
"""
from abc import ABC, abstractmethod
from typing import Optional

class INotificationService(ABC):
    """Contrato para servicios de notificación"""
    
    @abstractmethod
    def send_notification(self, message: str, subject: Optional[str] = None, is_error: bool = False) -> bool:
        """Envía notificación"""
        pass
    
    @abstractmethod
    def send_error_notification(self, error_message: str, context: Optional[dict] = None) -> bool:
        """Envía notificación de error"""
        pass

