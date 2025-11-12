"""
Interface para gestión de watermarks (ISP)
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class IWatermarkManager(ABC):
    """Contrato para gestión avanzada de watermarks (confirmación, estados, etc.)"""
    
    @abstractmethod
    def get_pending_watermark(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene watermark pendiente de confirmación"""
        pass
    
    @abstractmethod
    def confirm_watermark(self, table_name: str, column_name: str, timestamp: str,
                         additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Confirma un watermark pendiente"""
        pass
    
    @abstractmethod
    def delete_watermark(self, table_name: str, column_name: str, timestamp: str) -> bool:
        """Elimina un watermark específico"""
        pass

