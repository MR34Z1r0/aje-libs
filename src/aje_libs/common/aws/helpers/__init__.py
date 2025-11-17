"""
Helpers específicos de AWS
"""
from .s3_helper import S3Helper
from .dynamodb_helper import DynamoDBHelper
from .secrets_helper import SecretsHelper
from .ssm_helper import SSMParameterHelper
# BedrockHelper se importa de forma lazy - solo cuando se use explícitamente

__all__ = [
    'S3Helper',
    'DynamoDBHelper',
    'SecretsHelper',
    'SSMParameterHelper',
    'BedrockHelper',  # Mantener en __all__ para compatibilidad, pero importación lazy
]

# Importación lazy de BedrockHelper - solo se importa cuando se accede explícitamente
def __getattr__(name: str):
    """Importación lazy para BedrockHelper"""
    if name == 'BedrockHelper':
        from .bedrock_helper import BedrockHelper
        return BedrockHelper
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

