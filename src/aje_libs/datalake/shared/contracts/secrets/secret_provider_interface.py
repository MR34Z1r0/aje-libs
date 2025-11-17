# -*- coding: utf-8 -*-
"""
Interface para proveedores de secretos (DIP - Dependency Inversion Principle)
"""
from abc import ABC, abstractmethod
from typing import Union, Optional, Dict, Any


class ISecretProvider(ABC):
    """Interface para proveedores de secretos (abstrae AWS Secrets Manager, Vault, etc.)"""
    
    @abstractmethod
    def get_secret(self, secret_name: str, key: Optional[str] = None) -> Union[str, Dict[str, Any], None]:
        """
        Obtiene un secreto
        
        Args:
            secret_name: Nombre del secreto
            key: Clave específica dentro del secreto (opcional, si es JSON)
            
        Returns:
            Valor del secreto (string si key es None, valor de la key si se especifica)
            Dict si el secreto es JSON y key es None
            
        Raises:
            SecretNotFoundException: Si el secreto no existe
            KeyError: Si la key especificada no existe en el secreto
        """
        pass
    
    @abstractmethod
    def get_secret_value(self, secret_name: str, key_name: Optional[str] = None) -> Union[str, Dict[str, Any], None]:
        """
        Alias para get_secret (compatibilidad con SecretsHelper)
        
        Args:
            secret_name: Nombre del secreto
            key_name: Nombre de la clave dentro del secreto (opcional)
            
        Returns:
            Valor del secreto
        """
        pass

