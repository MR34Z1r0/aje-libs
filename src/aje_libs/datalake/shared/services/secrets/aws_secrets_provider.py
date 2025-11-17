# -*- coding: utf-8 -*-
"""
Implementación de ISecretProvider usando AWS Secrets Manager (DIP - Dependency Inversion)
"""
from typing import Union, Optional, Dict, Any
import json
import boto3
from botocore.exceptions import ClientError

from ...contracts.secrets import ISecretProvider
from ...services.logging import LoggerService
from aje_libs.common.aws.core import handle_aws_error, is_retryable_error  # ✅ Manejo de errores mejorado


class AWSSecretsProvider(ISecretProvider):
    """Implementación de ISecretProvider para AWS Secrets Manager"""
    
    def __init__(self, region: Optional[str] = None, logger_name: Optional[str] = None):
        """
        Inicializa el proveedor de secretos de AWS
        
        Args:
            region: Región de AWS (opcional)
            logger_name: Nombre del logger (opcional)
        """
        self.region = region
        self.client_sm = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")
        self.logger = LoggerService.get_logger(logger_name or __name__)
        self._cache: Dict[str, Dict[str, Any]] = {}  # Cache de secretos parseados
    
    def get_secret(self, secret_name: str, key: Optional[str] = None) -> Union[str, Dict[str, Any], None]:
        """
        Obtiene un secreto de AWS Secrets Manager
        
        Args:
            secret_name: Nombre del secreto
            key: Clave específica dentro del secreto (opcional, si es JSON)
            
        Returns:
            Valor del secreto (string si key es None y el secreto es string)
            Dict si el secreto es JSON y key es None
            Valor de la key si se especifica
        """
        try:
            # Obtener el valor del secreto
            secret_value = self.client_sm.get_secret_value(SecretId=secret_name)
            secret_string = secret_value["SecretString"]
            
            # Intentar parsear como JSON
            try:
                parsed_secret = json.loads(secret_string)
                self._cache[secret_name] = parsed_secret
                
                if key:
                    if not isinstance(parsed_secret, dict):
                        raise KeyError(f"El secreto '{secret_name}' no es un JSON válido con claves")
                    if key not in parsed_secret:
                        raise KeyError(f"La clave '{key}' no existe en el secreto '{secret_name}'")
                    # ✅ Seguridad: No loguear el valor del secreto, solo confirmación
                    self.logger.debug(f"✅ Clave '{key}' obtenida exitosamente del secreto '{secret_name}'")
                    return parsed_secret[key]
                else:
                    # ✅ Seguridad: Si retornamos todo el secreto, no loguear su contenido
                    self.logger.debug(f"✅ Contenido completo del secreto '{secret_name}' obtenido exitosamente")
                    return parsed_secret
            except json.JSONDecodeError:
                # Si no es JSON, retornar como string
                if key:
                    raise ValueError(f"El secreto '{secret_name}' no es JSON, no se puede extraer la clave '{key}'")
                # ✅ Seguridad: No loguear el contenido del secreto
                self.logger.debug(f"✅ Secreto '{secret_name}' obtenido como string (no JSON)")
                return secret_string
                
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"obtener secreto de AWS Secrets Manager (secret_name={secret_name})", self.logger)
            raise e
        except KeyError as e:
            self.logger.error(f"Error de clave en secreto: {e}")
            raise e
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar el secreto como JSON: {e}")
            raise ValueError(f"El contenido del secreto '{secret_name}' no es un JSON válido: {e}")
    
    def get_secret_value(self, secret_name: str, key_name: Optional[str] = None) -> Union[str, Dict[str, Any], None]:
        """
        Alias para get_secret (compatibilidad con SecretsHelper)
        
        Args:
            secret_name: Nombre del secreto
            key_name: Nombre de la clave dentro del secreto (opcional)
            
        Returns:
            Valor del secreto
        """
        return self.get_secret(secret_name, key_name)

