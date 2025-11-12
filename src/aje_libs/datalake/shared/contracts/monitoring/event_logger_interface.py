"""
Interface para registro de eventos (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IEventLogger(ABC):
    """Contrato para registro de eventos específicos"""
    
    @abstractmethod
    def log_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Registra un evento"""
        pass
    
    @abstractmethod
    def log_process_status(self, status: str, message: str, table_name: str, 
                          job_name: str = "", context: Optional[Dict[str, Any]] = None) -> str:
        """Registra estado de proceso"""
        pass

