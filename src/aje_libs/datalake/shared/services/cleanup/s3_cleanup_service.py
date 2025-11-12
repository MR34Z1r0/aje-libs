"""
Servicio de limpieza S3 - Implementa IResourceCleaner (SRP)
"""
import boto3
from typing import Dict, Any, List, Optional

from ...contracts.cleanup import IResourceCleaner
from ...contracts.logging import ILogger


class S3CleanupService(IResourceCleaner):
    """
    Servicio de limpieza S3 que implementa IResourceCleaner (SRP)
    Maneja eliminación de objetos en S3
    """
    
    def __init__(
        self,
        s3_client=None,
        logger: Optional[ILogger] = None
    ):
        """
        Inicializa el servicio de limpieza S3
        
        Args:
            s3_client: Cliente boto3 S3 (opcional, se crea si no se proporciona)
            logger: Logger para logs internos (DIP, opcional)
        """
        self.s3_client = s3_client or boto3.client('s3')
        self.logger = logger
    
    def delete_objects(self, resource_identifier: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Elimina objetos de S3
        
        Args:
            resource_identifier: Ruta S3 (s3://bucket/prefix o bucket/prefix)
            filters: Filtros adicionales (no usado actualmente)
            
        Returns:
            Dict con resultado: {'success': bool, 'items_deleted': int, 'errors': List[str]}
        """
        result = {
            'success': False,
            'items_deleted': 0,
            'errors': []
        }
        
        try:
            # Parsear ruta S3
            if resource_identifier.startswith('s3://'):
                resource_identifier = resource_identifier[5:]
            
            parts = resource_identifier.split('/', 1)
            bucket = parts[0]
            prefix = parts[1] if len(parts) > 1 else ''
            
            if self.logger:
                self.logger.info(f"Limpiando S3: s3://{bucket}/{prefix}")
            
            # Listar y eliminar objetos
            paginator = self.s3_client.get_paginator('list_objects_v2')
            total_objects = 0
            objects_to_delete = []
            
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
                        total_objects += 1
            
            if not objects_to_delete:
                result['success'] = True
                if self.logger:
                    self.logger.info(f"No hay objetos para eliminar en s3://{bucket}/{prefix}")
                return result
            
            # Eliminar en lotes de 1000 (límite de S3)
            deleted_count = 0
            batch_size = 1000
            
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i + batch_size]
                try:
                    delete_response = self.s3_client.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': batch}
                    )
                    
                    deleted_in_batch = len(delete_response.get('Deleted', []))
                    deleted_count += deleted_in_batch
                    
                    if self.logger:
                        self.logger.info(f"Batch {i//batch_size + 1}: Eliminados {deleted_in_batch} objetos")
                    
                    if 'Errors' in delete_response and delete_response['Errors']:
                        errors = [err.get('Message', 'Unknown error') for err in delete_response['Errors']]
                        result['errors'].extend(errors)
                        
                except Exception as e:
                    error_msg = f"Error eliminando batch {i//batch_size + 1}: {str(e)}"
                    result['errors'].append(error_msg)
                    if self.logger:
                        self.logger.error(error_msg)
            
            result['success'] = deleted_count > 0 or total_objects == 0
            result['items_deleted'] = deleted_count
            
            if self.logger:
                self.logger.info(f"✅ Limpieza S3 completada: {deleted_count}/{total_objects} objetos eliminados")
            
        except Exception as e:
            error_msg = f"Error eliminando objetos de S3: {str(e)}"
            result['errors'].append(error_msg)
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def delete_by_time_range(
        self,
        resource_identifier: str,
        period_column: str,
        period_values: List[Any],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Elimina objetos por rango de tiempo/período
        
        Nota: Para S3, esto requiere lógica adicional basada en nombres de archivos/particiones
        Por ahora delega a delete_objects
        """
        # Implementación específica para S3 con particiones por período
        # Por ahora retornamos 0 y se implementará según necesidades específicas
        if self.logger:
            self.logger.warning("delete_by_time_range no implementado completamente para S3")
        return 0

