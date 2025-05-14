# Built-in imports
import os
import logging
from typing import Optional, Union
import uuid

# External imports
from aws_lambda_powertools import Logger

def custom_logger(
    name: Optional[str] = None,
    correlation_id: Optional[Union[str, uuid.UUID, None]] = None,
    service: Optional[str] = None,
    owner: Optional[str] = None,
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
) -> Logger:
    """
    Returns a custom Logger Object with optional file logging capability.
    
    :param name: Logger name
    :param correlation_id: Correlation ID for tracing
    :param service: Service name
    :param owner: Owner name
    :param log_file: Optional path to log file. If provided, logs will also be written to this file
    :param log_level: Logging level for file logger (default: logging.INFO)
    :return: aws_lambda_powertools.Logger object
    """
    # Create the standard powertools logger
    powertools_logger = Logger(
        name=name,
        correlation_id=correlation_id,
        service=service,
        owner=owner,
        log_uncaught_exceptions=True,
    )
    
    # If log_file is provided, set up file logging
    if log_file:
        # Create a standard Python logger for file logging
        file_logger = logging.getLogger(f"{name}_file") if name else logging.getLogger("file_logger")
        file_logger.setLevel(log_level)
        
        # Clear existing handlers to avoid duplicates
        if file_logger.handlers:
            file_logger.handlers = []
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        file_logger.addHandler(file_handler)
        
        # Monkey patch the powertools_logger to also log to file
        original_info = powertools_logger.info
        original_error = powertools_logger.error
        original_warning = powertools_logger.warning
        original_debug = powertools_logger.debug
        
        def patched_info(msg, *args, **kwargs):
            original_info(msg, *args, **kwargs)
            file_logger.info(msg)
            
        def patched_error(msg, *args, **kwargs):
            original_error(msg, *args, **kwargs)
            file_logger.error(msg)
            
        def patched_warning(msg, *args, **kwargs):
            original_warning(msg, *args, **kwargs)
            file_logger.warning(msg)
            
        def patched_debug(msg, *args, **kwargs):
            original_debug(msg, *args, **kwargs)
            file_logger.debug(msg)
        
        # Replace the methods
        powertools_logger.info = patched_info
        powertools_logger.error = patched_error
        powertools_logger.warning = patched_warning
        powertools_logger.debug = patched_debug
    
    return powertools_logger