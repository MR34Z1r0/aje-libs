"""
Módulo common - Utilidades comunes
✅ Reorganizado multi-cloud:
- common/aws/helpers/ - Helpers específicos de AWS
- common/gcp/helpers/ - Helpers para GCP (futuro)
- common/shared/ - Código compartido (logger, utils)
"""
# ✅ Importar desde shared (código común)
from .shared import custom_logger, set_logger_config, DecimalEncoder

# ✅ Importar desde aws (helpers específicos de AWS y core utilities)
from .aws import (
    S3Helper,
    DynamoDBHelper,
    SecretsHelper,
    SSMParameterHelper,
    BotoSessionManager,
    handle_aws_error,
    is_retryable_error,
    # BedrockHelper se importa de forma lazy
)

# ✅ Importar helpers de Bedrock
from .aws.helpers.bedrock import (
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

__all__ = [
    # Shared (común)
    'custom_logger',
    'set_logger_config',
    'DecimalEncoder',
    # AWS Helpers
    'S3Helper',
    'DynamoDBHelper',
    'SecretsHelper',
    'SSMParameterHelper',
    'BedrockHelper',  # Mantener en __all__ para compatibilidad, pero importación lazy
    # AWS Core
    'BotoSessionManager',
    'handle_aws_error',
    'is_retryable_error',
    # Bedrock Models
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
]

# Importación lazy de BedrockHelper - solo se importa cuando se accede explícitamente
def __getattr__(name: str):
    """Importación lazy para BedrockHelper"""
    if name == 'BedrockHelper':
        from .aws.helpers import BedrockHelper
        return BedrockHelper
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
