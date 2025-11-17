# src/aje_libs/common/aws/helpers/secrets_helper.py
# Built-in imports
import json
import boto3
from typing import Union, Optional

# External imports
from botocore.exceptions import ClientError

# Own imports
from ...shared.logger import custom_logger

logger = custom_logger(__name__)

class SecretsHelper:
    """Ayudante personalizado para Secrets Manager que simplifica la obtención de secretos."""

    def __init__(self, secret_name: str) -> None:
        """
        :param secret_name (str): Nombre del secreto a recuperar.
        """
        self.secret_name = secret_name
        self.client_sm = boto3.client("secretsmanager")
        logger.debug(f"SecretsHelper inicializado para: {secret_name}")

    def get_secret_value(self, key_name: Optional[str] = None) -> Union[str, None]:
        """
        Obtiene el valor del secreto de AWS basado en una clave específica.
        :param key_name Optional(str): Nombre de la clave a recuperar del secreto JSON.
        """
        try:
            # Obtener el valor del secreto
            secret_value = self.client_sm.get_secret_value(SecretId=self.secret_name)
            
            # Parsear el valor del secreto
            self.json_secret = json.loads(secret_value["SecretString"])
            logger.debug("SecretString parseado correctamente")
            
            # ✅ Seguridad: No loguear valores de secretos
            # Devolver el valor específico o todo el secreto
            if key_name:
                logger.debug(f"✅ Clave '{key_name}' obtenida exitosamente del secreto '{self.secret_name}'")
                return self.json_secret[key_name]
            else:
                logger.debug(f"✅ Contenido completo del secreto '{self.secret_name}' obtenido exitosamente")
                return self.json_secret
                
        except ClientError as e:
            logger.error(f"Error al obtener el secreto de AWS: {self.secret_name}")
            logger.error(f"Código de error: {e.response['Error']['Code']}")
            logger.error(f"Mensaje de error: {e.response['Error']['Message']}")
            raise e
        except KeyError as e:
            logger.error(f"La clave solicitada no existe en el secreto: {key_name}")
            raise KeyError(f"La clave '{key_name}' no fue encontrada en el secreto")
        except json.JSONDecodeError as e:
            logger.error("Error al decodificar el secreto como JSON")
            raise ValueError("El contenido del secreto no es un JSON válido")
