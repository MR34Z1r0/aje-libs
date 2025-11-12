"""
Interface para almacenamiento de logs (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class ILogStorage(ABC):
    """Contrato para almacenamiento persistente de logs"""
    
    @abstractmethod
    def store_log(self, log_entry: Dict[str, Any]) -> bool:
        """Almacena una entrada de log"""
        pass
    
    @abstractmethod
    def get_logs(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene logs según filtros"""
        pass
    
    @abstractmethod
    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Limpia logs antiguos"""
        pass

