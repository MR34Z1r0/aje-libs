"""
Módulo common - Utilidades comunes
"""
from .helpers import (
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
    # BedrockHelper se importa de forma lazy - solo cuando se use explícitamente
    DynamoDBHelper,
    S3Helper,
    SecretsHelper,
    SSMParameterHelper,
)
from .logger import custom_logger, set_logger_config
from .utils import DecimalEncoder

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
    'custom_logger',
    'set_logger_config',
    'DecimalEncoder',
]

# Importación lazy de BedrockHelper - solo se importa cuando se accede explícitamente
def __getattr__(name: str):
    """Importación lazy para BedrockHelper"""
    if name == 'BedrockHelper':
        from .helpers import BedrockHelper
        return BedrockHelper
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")