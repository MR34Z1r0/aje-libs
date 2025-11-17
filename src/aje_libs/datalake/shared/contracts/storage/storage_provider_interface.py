# -*- coding: utf-8 -*-
"""
Interface para proveedores de almacenamiento (DIP - Dependency Inversion Principle)
Abstrae S3, Azure Blob Storage, GCS, etc.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import io


class IStorageProvider(ABC):
    """Interface para proveedores de almacenamiento (abstrae S3, Azure Blob, GCS, etc.)"""
    
    @abstractmethod
    def put_object(
        self,
        object_key: str,
        body: Union[str, bytes, io.IOBase],
        extra_args: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Sube un objeto al almacenamiento
        
        Args:
            object_key: Clave/nombre del objeto
            body: Contenido a subir (string, bytes, o file-like object)
            extra_args: Argumentos adicionales específicos del provider
            
        Returns:
            Ruta completa del objeto subido (ej: s3://bucket/key)
        """
        pass
    
    @abstractmethod
    def delete_objects(self, object_keys: List[str]) -> Dict[str, Any]:
        """
        Elimina múltiples objetos del almacenamiento
        
        Args:
            object_keys: Lista de claves/nombres de objetos a eliminar
            
        Returns:
            Dict con resultado: {'Deleted': [...], 'Errors': [...]}
        """
        pass
    
    @abstractmethod
    def list_objects(
        self, 
        prefix: str, 
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista objetos en el almacenamiento con un prefijo
        
        Args:
            prefix: Prefijo para filtrar objetos
            max_keys: Número máximo de objetos a retornar (opcional)
            
        Returns:
            Lista de dicts con información de objetos: [{'Key': '...', 'Size': ...}, ...]
        """
        pass
    
    @abstractmethod
    def object_exists(self, object_key: str) -> bool:
        """
        Verifica si un objeto existe en el almacenamiento
        
        Args:
            object_key: Clave/nombre del objeto
            
        Returns:
            True si el objeto existe, False en caso contrario
        """
        pass

