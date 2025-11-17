"""
Session Manager para Boto3
✅ Reutilización de conexiones y configuración centralizada
✅ Facilita mocking en tests
"""
from typing import Dict, Optional, Any
import boto3
from botocore.exceptions import ClientError

from ...shared.logger import custom_logger

logger = custom_logger(__name__)


class BotoSessionManager:
    """
    Singleton para gestionar sesiones Boto3 (reutilización y configuración centralizada).
    
    Este manager reutiliza sesiones y clientes de Boto3 para evitar crear múltiples
    conexiones y mejorar el rendimiento. También facilita el mocking en tests.
    
    Example:
        >>> # Obtener un cliente S3
        >>> s3_client = BotoSessionManager.get_client('s3', region='us-east-1')
        >>> 
        >>> # Obtener un cliente DynamoDB
        >>> dynamo_client = BotoSessionManager.get_client('dynamodb', region='us-east-1')
        >>> 
        >>> # Limpiar cache (útil para tests)
        >>> BotoSessionManager.clear_cache()
    """
    
    # Cache de sesiones por región y perfil
    _sessions: Dict[str, boto3.Session] = {}
    
    # Cache de clientes por servicio, región y perfil
    _clients: Dict[str, Any] = {}
    
    # Cache de recursos por servicio, región y perfil
    _resources: Dict[str, Any] = {}
    
    @classmethod
    def get_session(
        cls,
        region: Optional[str] = None,
        profile: Optional[str] = None
    ) -> boto3.Session:
        """
        Obtiene una sesión Boto3 (reutiliza si ya existe).
        
        Args:
            region: Región de AWS (opcional).
            profile: Perfil de AWS (opcional).
            
        Returns:
            Sesión Boto3 configurada.
        """
        key = f"{region or 'default'}_{profile or 'default'}"
        
        if key not in cls._sessions:
            cls._sessions[key] = boto3.Session(
                region_name=region,
                profile_name=profile
            )
            logger.debug(f"✅ Nueva sesión Boto3 creada: región={region}, perfil={profile}")
        
        return cls._sessions[key]
    
    @classmethod
    def get_client(
        cls,
        service: str,
        region: Optional[str] = None,
        profile: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Obtiene un cliente Boto3 para un servicio (reutiliza si ya existe).
        
        Args:
            service: Nombre del servicio AWS (ej: 's3', 'dynamodb', 'secretsmanager').
            region: Región de AWS (opcional).
            profile: Perfil de AWS (opcional).
            **kwargs: Argumentos adicionales para el cliente.
            
        Returns:
            Cliente Boto3 configurado.
            
        Example:
            >>> s3_client = BotoSessionManager.get_client('s3', region='us-east-1')
        """
        # Crear clave única para el cliente
        client_key = f"{service}_{region or 'default'}_{profile or 'default'}"
        key_parts = [client_key]
        if kwargs:
            # Incluir kwargs ordenados en la clave si son relevantes
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append("_".join(f"{k}={v}" for k, v in sorted_kwargs))
        client_key = "_".join(key_parts)
        
        if client_key not in cls._clients:
            session = cls.get_session(region, profile)
            cls._clients[client_key] = session.client(service, **kwargs)
            logger.debug(f"✅ Nuevo cliente Boto3 creado: {service}, región={region}, perfil={profile}")
        
        return cls._clients[client_key]
    
    @classmethod
    def get_resource(
        cls,
        service: str,
        region: Optional[str] = None,
        profile: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Obtiene un recurso Boto3 para un servicio (reutiliza si ya existe).
        
        Args:
            service: Nombre del servicio AWS (ej: 's3', 'dynamodb').
            region: Región de AWS (opcional).
            profile: Perfil de AWS (opcional).
            **kwargs: Argumentos adicionales para el recurso.
            
        Returns:
            Recurso Boto3 configurado.
            
        Example:
            >>> s3_resource = BotoSessionManager.get_resource('s3', region='us-east-1')
        """
        # Crear clave única para el recurso
        resource_key = f"{service}_{region or 'default'}_{profile or 'default'}"
        key_parts = [resource_key]
        if kwargs:
            # Incluir kwargs ordenados en la clave si son relevantes
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append("_".join(f"{k}={v}" for k, v in sorted_kwargs))
        resource_key = "_".join(key_parts)
        
        if resource_key not in cls._resources:
            session = cls.get_session(region, profile)
            cls._resources[resource_key] = session.resource(service, **kwargs)
            logger.debug(f"✅ Nuevo recurso Boto3 creado: {service}, región={region}, perfil={profile}")
        
        return cls._resources[resource_key]
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Limpia todos los caches (útil para tests o reinicio).
        
        Example:
            >>> # En tests
            >>> BotoSessionManager.clear_cache()
            >>> # Ahora se crearán nuevas sesiones/clientes
        """
        cls._sessions.clear()
        cls._clients.clear()
        cls._resources.clear()
        logger.debug("✅ Cache de BotoSessionManager limpiado")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """
        Obtiene estadísticas del cache.
        
        Returns:
            Diccionario con conteos de sesiones, clientes y recursos.
        """
        return {
            'sessions': len(cls._sessions),
            'clients': len(cls._clients),
            'resources': len(cls._resources),
        }


def handle_aws_error(error: ClientError, context: str, logger_instance=None) -> None:
    """
    Maneja errores de AWS de forma consistente.
    
    Args:
        error: Excepción ClientError de Boto3.
        context: Contexto donde ocurrió el error (ej: "obtener objeto S3").
        logger_instance: Logger opcional (si no se proporciona, usa el default).
        
    Raises:
        ClientError: Re-lanza el error después de loguearlo.
        
    Example:
        >>> try:
        ...     s3_client.get_object(Bucket='bucket', Key='key')
        ... except ClientError as e:
        ...     handle_aws_error(e, "obtener objeto S3", logger)
        ...     raise
    """
    if logger_instance is None:
        logger_instance = logger
    
    error_code = error.response.get('Error', {}).get('Code', 'Unknown')
    error_message = error.response.get('Error', {}).get('Message', 'Unknown error')
    request_id = error.response.get('ResponseMetadata', {}).get('RequestId', 'N/A')
    
    logger_instance.error(
        f"❌ Error de AWS al {context}: "
        f"Código={error_code}, Mensaje={error_message}, RequestId={request_id}"
    )
    
    # Log adicional según el tipo de error
    if error_code == 'ResourceNotFoundException':
        logger_instance.warning(f"⚠️  Recurso no encontrado al {context}")
    elif error_code == 'AccessDeniedException':
        logger_instance.error(f"🚫 Acceso denegado al {context} (verificar IAM)")
    elif error_code == 'ThrottlingException':
        logger_instance.warning(f"⏱️  Throttling al {context} (considerar retry con backoff)")
    elif error_code == 'ServiceUnavailableException':
        logger_instance.error(f"🔴 Servicio no disponible al {context}")


def is_retryable_error(error: ClientError) -> bool:
    """
    Determina si un error de AWS es retryable.
    
    Args:
        error: Excepción ClientError de Boto3.
        
    Returns:
        True si el error es retryable, False en caso contrario.
        
    Example:
        >>> try:
        ...     s3_client.get_object(Bucket='bucket', Key='key')
        ... except ClientError as e:
        ...     if is_retryable_error(e):
        ...         # Reintentar con backoff
        ...         pass
    """
    retryable_codes = [
        'ThrottlingException',
        'Throttling',
        'ServiceUnavailableException',
        'InternalServiceError',
        'InternalError',
        'RequestTimeout',
        'Timeout',
        'TooManyRequestsException',
        'ECONNRESET',
        'ENOTFOUND',
        'ETIMEDOUT',
    ]
    
    error_code = error.response.get('Error', {}).get('Code', 'Unknown')
    http_status = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
    
    # Errores HTTP 5xx son generalmente retryables
    if 500 <= http_status < 600:
        return True
    
    # Verificar código de error específico
    return error_code in retryable_codes

