"""
Helpers del módulo common
"""
from .bedrock import (
    ModelFactory,
    BaseBedrockModel,
    BedrockModel,
    BedrockModelCategory,
    AmazonModel,
    AnthropicModel,
    AI21Model,
    CohereModel,
    DeepSeekModel,
    MetaModel,
    NovaModel,
)
# Importación lazy para evitar importación automática innecesaria
# BedrockHelper solo se importará cuando se use explícitamente
from .dynamodb_helper import DynamoDBHelper
from .s3_helper import S3Helper
from .secrets_helper import SecretsHelper
from .ssm_helper import SSMParameterHelper

__all__ = [
    'ModelFactory',
    'BaseBedrockModel',
    'BedrockModel',
    'BedrockModelCategory',
    'AmazonModel',
    'AnthropicModel',
    'AI21Model',
    'CohereModel',
    'DeepSeekModel',
    'MetaModel',
    'NovaModel',
    'BedrockHelper',  # Mantener en __all__ para compatibilidad, pero importación lazy
    'DynamoDBHelper',
    'S3Helper',
    'SecretsHelper',
    'SSMParameterHelper',
]

# Importación lazy de BedrockHelper - solo se importa cuando se accede explícitamente
def __getattr__(name: str):
    """Importación lazy para BedrockHelper"""
    if name == 'BedrockHelper':
        from .bedrock_helper import BedrockHelper
        return BedrockHelper
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")