# -*- coding: utf-8 -*-
"""
Implementación de IStorageProvider usando AWS S3 (DIP - Dependency Inversion)
"""
from typing import List, Dict, Any, Optional, Union
import io
from botocore.exceptions import ClientError

from ...contracts.storage import IStorageProvider
from ...services.logging import LoggerService

# ✅ DIP: Importar S3Helper solo para compatibilidad, idealmente debería ser inyectado
from aje_libs.common.aws.helpers.s3_helper import S3Helper


class S3StorageProvider(IStorageProvider):
    """Implementación de IStorageProvider para AWS S3"""
    
    def __init__(
        self,
        bucket_name: str,
        region: Optional[str] = None,
        logger_name: Optional[str] = None
    ):
        """
        Inicializa el proveedor de almacenamiento S3
        
        Args:
            bucket_name: Nombre del bucket S3
            region: Región de AWS (opcional)
            logger_name: Nombre del logger (opcional)
        """
        self.bucket_name = bucket_name
        self.region = region
        self.logger = LoggerService.get_logger(logger_name or __name__)
        
        # ✅ DIP: Usar S3Helper internamente (paso intermedio)
        # En el futuro, podríamos inyectar IStorageProvider directamente
        self._s3_helper = S3Helper(bucket_name, region_name=region)
    
    def put_object(
        self,
        object_key: str,
        body: Union[str, bytes, io.IOBase],
        extra_args: Optional[Dict[str, Any]] = None
    ) -> str:
        """Sube un objeto a S3"""
        try:
            return self._s3_helper.put_object(object_key, body, extra_args)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            self.logger.error(f"Error al subir objeto a S3: {object_key}")
            self.logger.error(f"Código de error: {error_code}, Mensaje: {error_message}")
            raise
    
    def delete_objects(self, object_keys: List[str]) -> Dict[str, Any]:
        """Elimina múltiples objetos de S3"""
        try:
            return self._s3_helper.delete_objects(object_keys)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            self.logger.error(f"Error al eliminar objetos de S3: {len(object_keys)} objetos")
            self.logger.error(f"Código de error: {error_code}, Mensaje: {error_message}")
            raise
    
    def list_objects(
        self, 
        prefix: str, 
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Lista objetos en S3 con un prefijo"""
        try:
            # Si max_keys es None, no pasarlo (s3_helper usará su default de 1000)
            if max_keys is not None:
                return self._s3_helper.list_objects(prefix, max_keys=max_keys)
            else:
                return self._s3_helper.list_objects(prefix)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            self.logger.error(f"Error al listar objetos en S3: prefix={prefix}")
            self.logger.error(f"Código de error: {error_code}, Mensaje: {error_message}")
            raise
    
    def object_exists(self, object_key: str) -> bool:
        """Verifica si un objeto existe en S3"""
        try:
            return self._s3_helper.object_exists(object_key)
        except ClientError:
            # Si hay error, asumir que no existe
            return False

