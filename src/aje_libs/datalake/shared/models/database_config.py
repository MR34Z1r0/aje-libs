# -*- coding: utf-8 -*-
"""
Configuración de base de datos compartida.
Movido desde extract_data/models a shared/models para uso compartido.
"""
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class DatabaseConfig:
    """
    Configuración de base de datos.
    
    Attributes:
        endpoint_name: Nombre único del endpoint de base de datos.
        db_type: Tipo de base de datos ('sqlserver', 'postgresql', 'oracle', 'mysql', 'mariadb').
        server: Dirección del servidor de base de datos.
        database: Nombre de la base de datos.
        username: Usuario para conectarse.
        secret_key: Clave dentro del secreto para obtener la contraseña.
        secret_name: Nombre del secreto en AWS Secrets Manager.
        port: Puerto de conexión (opcional, usa default según db_type si no se especifica).
        
    Example:
        >>> config = DatabaseConfig(
        ...     endpoint_name="prod-sql-server",
        ...     db_type="sqlserver",
        ...     server="my-server.database.windows.net",
        ...     database="mydb",
        ...     username="admin",
        ...     secret_key="password",
        ...     secret_name="prod/datalake/sql/password"
        ... )
    """
    endpoint_name: str
    db_type: str  # 'sqlserver', 'postgresql', 'oracle', 'mysql', 'mariadb'
    server: str
    database: str
    username: str
    secret_key: str  # Key to get password from secrets
    secret_name: str
    port: Optional[int] = None
    
    # Default ports por tipo de DB
    _DEFAULT_PORTS = {
        'sqlserver': 1433,
        'mssql': 1433,
        'postgresql': 5432,
        'postgres': 5432,
        'oracle': 1521,
        'mysql': 3306,
        'mariadb': 3306,
    }
    
    def __post_init__(self):
        """
        Valida que todos los campos requeridos estén presentes y sean válidos.
        
        Raises:
            ValueError: Si algún campo requerido está vacío o es inválido.
        """
        # Validar campos requeridos
        required_fields = {
            'endpoint_name': self.endpoint_name,
            'db_type': self.db_type,
            'server': self.server,
            'database': self.database,
            'username': self.username,
            'secret_key': self.secret_key,
            'secret_name': self.secret_name,
        }
        
        missing_fields = [
            field for field, value in required_fields.items()
            if not value or (isinstance(value, str) and not value.strip())
        ]
        
        if missing_fields:
            raise ValueError(
                f"Campos requeridos faltantes o vacíos para DatabaseConfig: {missing_fields}"
            )
        
        # Validar db_type
        db_type_lower = self.db_type.lower()
        valid_db_types = list(self._DEFAULT_PORTS.keys())
        if db_type_lower not in valid_db_types:
            raise ValueError(
                f"db_type '{self.db_type}' no es válido. "
                f"Disponibles: {', '.join(valid_db_types)}"
            )
        
        # Validar formato de server (básico)
        if not self.server or len(self.server.strip()) < 3:
            raise ValueError(f"Server '{self.server}' no es válido (muy corto)")
        
        # Validar formato de database name (básico)
        if not re.match(r'^[a-zA-Z0-9_][a-zA-Z0-9_\-]*$', self.database):
            raise ValueError(
                f"Database name '{self.database}' contiene caracteres inválidos. "
                f"Debe empezar con letra/número y contener solo letras, números, guiones y guiones bajos"
            )
        
        # Validar formato de username (básico)
        if not re.match(r'^[a-zA-Z0-9_][a-zA-Z0-9_@.\-]*$', self.username):
            raise ValueError(
                f"Username '{self.username}' contiene caracteres inválidos"
            )
        
        # Validar secret_name (debe seguir formato esperado)
        if not self.secret_name or '/' not in self.secret_name:
            # Warning: secret_name debería seguir formato {env}/{project}/{team}/{source}
            # pero no fallar si no lo hace
            pass
        
        # Asignar puerto por defecto si no se especificó
        if self.port is None:
            object.__setattr__(self, 'port', self._DEFAULT_PORTS.get(db_type_lower))
        
        # Validar rango de puerto
        if self.port is not None and (self.port < 1 or self.port > 65535):
            raise ValueError(f"Puerto {self.port} está fuera del rango válido (1-65535)")
    
    def get_connection_string(self, password: str) -> str:
        """
        Genera string de conexión según el tipo de DB.
        
        Args:
            password: Contraseña para la conexión.
            
        Returns:
            String de conexión formateado.
        """
        db_type_lower = self.db_type.lower()
        port = self.port or self._DEFAULT_PORTS.get(db_type_lower, 1433)
        
        if db_type_lower in ['sqlserver', 'mssql']:
            return (
                f"mssql+pymssql://{self.username}:{password}"
                f"@{self.server}:{port}/{self.database}"
                f"?charset=utf8&timeout=900&login_timeout=900"
            )
        elif db_type_lower in ['postgresql', 'postgres']:
            return f"postgresql://{self.username}:{password}@{self.server}:{port}/{self.database}"
        elif db_type_lower == 'oracle':
            return f"oracle://{self.username}:{password}@{self.server}:{port}/{self.database}"
        elif db_type_lower in ['mysql', 'mariadb']:
            return f"mysql+pymysql://{self.username}:{password}@{self.server}:{port}/{self.database}"
        else:
            raise ValueError(f"Tipo de base de datos '{self.db_type}' no soportado para connection string")

