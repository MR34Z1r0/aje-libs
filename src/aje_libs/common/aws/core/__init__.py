"""
Core AWS utilities - Session Management y manejo de errores
"""
from .boto_session_manager import (
    BotoSessionManager,
    handle_aws_error,
    is_retryable_error,
)

__all__ = [
    'BotoSessionManager',
    'handle_aws_error',
    'is_retryable_error',
]

