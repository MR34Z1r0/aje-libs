"""
Interface para limpiadores de recursos específicos (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IResourceCleaner(ABC):
    """Contrato para limpiadores de recursos específicos (S3, DynamoDB, etc.)"""
    
    @abstractmethod
    def delete_objects(self, resource_identifier: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Elimina objetos del recurso
        
        Args:
            resource_identifier: Identificador del recurso (bucket/prefix, table_name, etc.)
            filters: Filtros adicionales para la limpieza
            
        Returns:
            Dict con resultado: {'success': bool, 'items_deleted': int, 'errors': List[str]}
        """
        pass
    
    @abstractmethod
    def delete_by_time_range(self, resource_identifier: str, period_column: str, 
                            period_values: List[Any], additional_filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Elimina objetos por rango de tiempo/período
        
        Returns:
            Cantidad de items eliminados
        """
        pass

