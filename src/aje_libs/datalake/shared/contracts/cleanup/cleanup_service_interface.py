"""
Interface para servicios de limpieza (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ICleanupService(ABC):
    """Contrato para servicios de limpieza de recursos"""
    
    @abstractmethod
    def cleanup(self, resource_path: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Limpia recursos en la ruta especificada
        
        Returns:
            Dict con resultado: {'success': bool, 'items_deleted': int, 'errors': List[str]}
        """
        pass
    
    @abstractmethod
    def cleanup_table_data(self, table_path: str) -> Dict[str, Any]:
        """Limpia datos de una tabla específica"""
        pass

