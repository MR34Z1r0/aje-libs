"""
Servicio de limpieza compartido - Implementa ICleanupService (SRP)
"""
from typing import Dict, Any, List, Optional

from ...contracts.cleanup import ICleanupService, IResourceCleaner
from ...contracts.logging import ILogger


class CleanupService(ICleanupService):
    """
    Servicio de limpieza que implementa ICleanupService (SRP)
    Coordina múltiples limpiadores de recursos
    """
    
    def __init__(
        self,
        resource_cleaners: List[IResourceCleaner],
        logger: Optional[ILogger] = None
    ):
        """
        Inicializa el servicio de limpieza
        
        Args:
            resource_cleaners: Lista de limpiadores de recursos (DIP)
            logger: Logger para logs internos (DIP, opcional)
        """
        self.resource_cleaners = resource_cleaners
        self.logger = logger
    
    def cleanup(self, resource_path: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Limpia recursos en la ruta especificada
        
        Returns:
            Dict con resultado consolidado
        """
        consolidated_result = {
            'success': True,
            'total_items_deleted': 0,
            'services_results': [],
            'errors': []
        }
        
        for cleaner in self.resource_cleaners:
            try:
                result = cleaner.delete_objects(resource_path, filters)
                consolidated_result['services_results'].append(result)
                consolidated_result['total_items_deleted'] += result.get('items_deleted', 0)
                
                if not result.get('success', False):
                    consolidated_result['success'] = False
                
                if result.get('errors'):
                    consolidated_result['errors'].extend(result['errors'])
            except Exception as e:
                error_msg = f"Error en limpiador {type(cleaner).__name__}: {str(e)}"
                consolidated_result['errors'].append(error_msg)
                consolidated_result['success'] = False
                
                if self.logger:
                    self.logger.error(error_msg)
        
        return consolidated_result
    
    def cleanup_table_data(self, table_path: str) -> Dict[str, Any]:
        """Limpia datos de una tabla específica"""
        return self.cleanup(table_path)

