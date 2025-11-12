"""
Interface para servicios de logging (ISP - Interface Segregation Principle)
"""
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

class ILogger(ABC):
    """Contrato para servicios de logging"""
    
    @abstractmethod
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra mensaje de debug"""
        pass
    
    @abstractmethod
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra mensaje informativo"""
        pass
    
    @abstractmethod
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra advertencia"""
        pass
    
    @abstractmethod
    def error(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None):
        """Registra error"""
        pass
    
    @abstractmethod
    def critical(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None):
        """Registra error crítico"""
        pass

