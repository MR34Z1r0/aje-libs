"""
Módulo AWS - Helpers específicos de AWS y Core utilities
"""
from .helpers import (
    S3Helper,
    DynamoDBHelper,
    SecretsHelper,
    SSMParameterHelper,
    # BedrockHelper se importa de forma lazy
)
from .core import (
    BotoSessionManager,
    handle_aws_error,
    is_retryable_error,
)

__all__ = [
    'S3Helper',
    'DynamoDBHelper',
    'SecretsHelper',
    'SSMParameterHelper',
    'BedrockHelper',  # Mantener en __all__ para compatibilidad, pero importación lazy
    'BotoSessionManager',
    'handle_aws_error',
    'is_retryable_error',
]

# Importación lazy de BedrockHelper
def __getattr__(name: str):
    """Importación lazy para BedrockHelper"""
    if name == 'BedrockHelper':
        from .helpers import BedrockHelper
        return BedrockHelper
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

