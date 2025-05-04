# Built-in imports
from typing import Optional, Union
import uuid

# External imports
from aws_lambda_powertools import Logger


def custom_logger(
    correlation_id: Optional[Union[str, uuid.UUID, None]] = None,
    owner: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Logger:
    """Returns a custom <aws_lambda_powertools.Logger> Object."""
    return Logger(
        service=project_name,
        owner=owner,
        correlation_id=correlation_id,
        log_uncaught_exceptions=True,
    )
