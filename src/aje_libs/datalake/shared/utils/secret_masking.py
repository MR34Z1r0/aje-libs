"""
Utilidades para enmascarar secretos y datos sensibles en logs
✅ Seguridad: Evita exposición accidental de credenciales
"""
import re
from typing import Any, Dict, List


def mask_secret(value: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """
    Enmascara un secreto mostrando solo los últimos caracteres visibles.
    
    Args:
        value: Valor a enmascarar.
        visible_chars: Número de caracteres visibles al final (default: 4).
        mask_char: Carácter para usar como máscara (default: "*").
        
    Returns:
        Valor enmascarado.
        
    Example:
        >>> mask_secret("my_secret_password_123")
        '******************23'
    """
    if not value:
        return "***"
    
    if len(value) <= visible_chars:
        return mask_char * len(value)
    
    return mask_char * (len(value) - visible_chars) + value[-visible_chars:]


def mask_secret_partial(value: str, visible_start: int = 3, visible_end: int = 3) -> str:
    """
    Enmascara un secreto mostrando algunos caracteres al inicio y al final.
    
    Args:
        value: Valor a enmascarar.
        visible_start: Número de caracteres visibles al inicio (default: 3).
        visible_end: Número de caracteres visibles al final (default: 3).
        
    Returns:
        Valor enmascarado.
        
    Example:
        >>> mask_secret_partial("my_secret_password_123")
        'my_****************123'
    """
    if not value:
        return "***"
    
    total_visible = visible_start + visible_end
    if len(value) <= total_visible:
        return "*" * len(value)
    
    return (
        value[:visible_start] + 
        "*" * (len(value) - total_visible) + 
        value[-visible_end:]
    )


def mask_dict_secrets(data: Dict[str, Any], secret_keys: List[str] = None) -> Dict[str, Any]:
    """
    Enmascara valores sensibles en un diccionario.
    
    Args:
        data: Diccionario que puede contener secretos.
        secret_keys: Lista de claves que contienen secretos. 
                    Si es None, usa claves comunes por defecto.
        
    Returns:
        Diccionario con valores enmascarados.
    """
    if secret_keys is None:
        secret_keys = [
            'password', 'passwd', 'pwd',
            'secret', 'secret_key', 'api_key', 'access_key',
            'token', 'access_token', 'refresh_token',
            'credential', 'credentials',
            'authorization', 'auth',
        ]
    
    masked_data = {}
    for key, value in data.items():
        key_lower = key.lower()
        # Verificar si la clave contiene alguna palabra clave de secreto
        if any(secret_key in key_lower for secret_key in secret_keys):
            if isinstance(value, str):
                masked_data[key] = mask_secret(value)
            elif isinstance(value, dict):
                masked_data[key] = mask_dict_secrets(value, secret_keys)
            else:
                masked_data[key] = "***"
        elif isinstance(value, dict):
            masked_data[key] = mask_dict_secrets(value, secret_keys)
        else:
            masked_data[key] = value
    
    return masked_data


def sanitize_log_message(message: str, secret_patterns: List[str] = None) -> str:
    """
    Sanitiza un mensaje de log eliminando patrones que podrían contener secretos.
    
    Args:
        message: Mensaje de log a sanitizar.
        secret_patterns: Patrones regex a buscar y enmascarar.
                        Si es None, usa patrones comunes.
        
    Returns:
        Mensaje sanitizado.
    """
    if secret_patterns is None:
        # Patrones comunes de secretos en mensajes
        secret_patterns = [
            r'(?i)password["\s:=]+([^\s,}]+)',
            r'(?i)secret["\s:=]+([^\s,}]+)',
            r'(?i)token["\s:=]+([^\s,}]+)',
            r'(?i)api[_-]?key["\s:=]+([^\s,}]+)',
            r'(?i)access[_-]?key["\s:=]+([^\s,}]+)',
        ]
    
    sanitized = message
    for pattern in secret_patterns:
        # Reemplazar valores encontrados con versión enmascarada
        def replace_secret(match):
            secret_value = match.group(1) if match.lastindex else match.group(0)
            return match.group(0).replace(secret_value, mask_secret(secret_value))
        
        sanitized = re.sub(pattern, replace_secret, sanitized)
    
    return sanitized


def is_secret_key(key_name: str) -> bool:
    """
    Verifica si un nombre de clave sugiere que contiene un secreto.
    
    Args:
        key_name: Nombre de la clave a verificar.
        
    Returns:
        True si probablemente es un secreto.
    """
    secret_keywords = [
        'password', 'passwd', 'pwd',
        'secret', 'secret_key', 'api_key', 'access_key',
        'token', 'access_token', 'refresh_token',
        'credential', 'credentials',
        'authorization', 'auth',
    ]
    
    key_lower = key_name.lower()
    return any(keyword in key_lower for keyword in secret_keywords)

