"""
Servicio de logging compartido - Implementa ILogger (SRP)
"""
import os
import logging
import datetime as dt
from typing import Optional, Dict, Any
import platform

from ...contracts.logging import ILogger

# External imports - conditional import for aws_lambda_powertools
try:
    from aws_lambda_powertools import Logger as PowertoolsLogger
    POWERTOOLS_AVAILABLE = True
except ImportError:
    PowertoolsLogger = None
    POWERTOOLS_AVAILABLE = False


class LoggerService(ILogger):
    """
    Servicio de logging que implementa ILogger (SRP)
    Maneja automáticamente AWS CloudWatch y archivos locales
    """
    
    # Configuración global por defecto
    _global_config = {
        'log_level': logging.INFO,
        'log_directory': './logs',
        'service_name': 'datalake',
        'correlation_id': None,
        'owner': None,
        'auto_detect_env': True,
        'force_local_mode': False
    }
    
    # Cache de loggers para evitar recrear
    _logger_cache = {}
    
    # Cache de file handlers para reutilizar el MISMO archivo
    _file_handler_cache = {}
    
    def __init__(self, logger_name: Optional[str] = None):
        """
        Inicializa el servicio de logging
        
        Args:
            logger_name: Nombre del logger (normalmente __name__)
        """
        self.logger_name = logger_name or __name__
        self._logger = self._get_logger()
    
    @classmethod
    def configure_global(cls, 
                        log_level: Optional[int] = None,
                        log_directory: Optional[str] = None, 
                        service_name: Optional[str] = None,
                        correlation_id: Optional[str] = None,
                        owner: Optional[str] = None,
                        auto_detect_env: bool = True,
                        force_local_mode: bool = False):
        """Configura parámetros globales para todos los loggers"""
        if log_level is not None:
            cls._global_config['log_level'] = log_level
        if log_directory is not None:
            cls._global_config['log_directory'] = log_directory
        if service_name is not None:
            cls._global_config['service_name'] = service_name
        if correlation_id is not None:
            cls._global_config['correlation_id'] = correlation_id
        if owner is not None:
            cls._global_config['owner'] = owner
        
        cls._global_config['auto_detect_env'] = auto_detect_env
        cls._global_config['force_local_mode'] = force_local_mode
        cls._logger_cache.clear()
    
    def _get_logger(self) -> logging.Logger:
        """Obtiene el logger configurado"""
        cache_key = self.logger_name
        
        if cache_key in self._logger_cache:
            return self._logger_cache[cache_key]
        
        is_aws = self._is_aws_environment() and not self._global_config['force_local_mode']
        
        if is_aws and POWERTOOLS_AVAILABLE:
            logger = self._create_powertools_logger()
        else:
            logger = self._create_local_logger()
        
        self._logger_cache[cache_key] = logger
        return logger
    
    def _is_aws_environment(self) -> bool:
        """Detecta si está corriendo en AWS"""
        aws_indicators = [
            'AWS_EXECUTION_ENV',
            'AWS_LAMBDA_FUNCTION_NAME',
            'GLUE_VERSION',
            'AWS_REGION'
        ]
        return any(os.getenv(indicator) for indicator in aws_indicators)
    
    def _create_powertools_logger(self) -> logging.Logger:
        """Crea logger usando AWS Lambda Powertools"""
        if not POWERTOOLS_AVAILABLE:
            return self._create_local_logger()
        
        logger = PowertoolsLogger(
            service=self._global_config['service_name'],
            level=logging.getLevelName(self._global_config['log_level']),
            stream=None,
            logger_handler=None
        )
        
        if self._global_config.get('correlation_id'):
            logger.append_keys(correlation_id=self._global_config['correlation_id'])
        
        if self._global_config.get('owner'):
            logger.append_keys(owner=self._global_config['owner'])
        
        # Agregar file handler si está configurado
        log_file_path = self._get_log_file_path()
        if log_file_path and log_file_path not in self._file_handler_cache:
            try:
                file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
                file_handler.setLevel(self._global_config['log_level'])
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                self._file_handler_cache[log_file_path] = file_handler
            except Exception as e:
                print(f"WARNING: Could not create log file handler: {e}")
        
        if log_file_path and log_file_path in self._file_handler_cache:
            file_handler = self._file_handler_cache[log_file_path]
            if file_handler not in logger.handlers:
                logger.addHandler(file_handler)
        
        return logger
    
    def _create_local_logger(self) -> logging.Logger:
        """Crea logger local que escribe a archivo y consola"""
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self._global_config['log_level'])
        logger.handlers.clear()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._global_config['log_level'])
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler para archivo (compartido)
        log_file_path = self._get_log_file_path()
        if log_file_path:
            if log_file_path not in self._file_handler_cache:
                try:
                    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
                    file_handler.setLevel(self._global_config['log_level'])
                    file_handler.setFormatter(formatter)
                    self._file_handler_cache[log_file_path] = file_handler
                except Exception as e:
                    print(f"WARNING: Could not create log file {log_file_path}: {e}")
            
            if log_file_path in self._file_handler_cache:
                file_handler = self._file_handler_cache[log_file_path]
                if file_handler not in logger.handlers:
                    logger.addHandler(file_handler)
        
        logger.propagate = False
        return logger
    
    def _get_log_file_path(self) -> Optional[str]:
        """Genera ruta para archivo de log"""
        log_dir = self._global_config['log_directory']
        
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"WARNING: Could not create log directory {log_dir}: {e}")
            return None
        
        timestamp = dt.datetime.now().strftime('%Y%m%d')
        safe_service_name = self._global_config['service_name'].replace('.', '_').replace(' ', '_')
        filename = f"{safe_service_name}_{timestamp}.log"
        
        return os.path.join(log_dir, filename)
    
    # Implementación de ILogger
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra mensaje de debug"""
        self._logger.debug(message, extra=extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra mensaje informativo"""
        self._logger.info(message, extra=extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Registra advertencia"""
        self._logger.warning(message, extra=extra)
    
    def error(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None):
        """Registra error"""
        self._logger.error(message, exc_info=exc_info, extra=extra)
    
    def critical(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None):
        """Registra error crítico"""
        self._logger.critical(message, exc_info=exc_info, extra=extra)
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        Método de conveniencia para obtener logger (compatibilidad con código existente)
        """
        service = cls(name)
        return service._logger
    
    @classmethod
    def print_environment_info(cls):
        """Imprime información del entorno de logging"""
        is_aws = any(os.getenv(var) for var in ['AWS_EXECUTION_ENV', 'AWS_LAMBDA_FUNCTION_NAME', 'GLUE_VERSION', 'AWS_REGION'])
        force_local = cls._global_config['force_local_mode']
        
        print("=" * 60)
        print("DATALAKE LOGGING ENVIRONMENT INFO")
        print("=" * 60)
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python: {platform.python_version()}")
        print(f"AWS Environment Detected: {is_aws}")
        print(f"PowerTools Available: {POWERTOOLS_AVAILABLE}")
        print(f"Force Local Mode: {force_local}")
        print(f"Log Level: {logging.getLevelName(cls._global_config['log_level'])}")
        print(f"Log Directory: {cls._global_config['log_directory']}")
        print(f"Service Name: {cls._global_config['service_name']}")
        print("=" * 60)

