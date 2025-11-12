"""
Interface para servicios de monitoreo (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IMonitor(ABC):
    """Contrato para servicios de monitoreo de procesos"""
    
    @abstractmethod
    def log_start(self, table_name: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra inicio de proceso. Retorna process_id"""
        pass
    
    @abstractmethod
    def log_success(self, table_name: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra éxito de proceso. Retorna process_id"""
        pass
    
    @abstractmethod
    def log_error(self, table_name: str, error_message: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra error de proceso. Retorna process_id"""
        pass
    
    @abstractmethod
    def log_warning(self, table_name: str, warning_message: str, job_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Registra advertencia de proceso. Retorna process_id"""
        pass

