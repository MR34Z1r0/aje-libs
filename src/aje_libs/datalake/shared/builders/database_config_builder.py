# -*- coding: utf-8 -*-
"""
Builder para DatabaseConfig (Builder Pattern - mejor UX para construcción de configs)
"""
from typing import Optional
from ..models import DatabaseConfig


class DatabaseConfigBuilder:
    """Builder para construir DatabaseConfig de forma fluida"""
    
    def __init__(self):
        """Inicializa el builder con valores por defecto"""
        self._config: dict = {}
    
    def with_endpoint_name(self, endpoint_name: str) -> 'DatabaseConfigBuilder':
        """Establece el nombre del endpoint"""
        self._config['endpoint_name'] = endpoint_name
        return self
    
    def with_db_type(self, db_type: str) -> 'DatabaseConfigBuilder':
        """Establece el tipo de base de datos"""
        self._config['db_type'] = db_type.lower()
        return self
    
    def with_server(self, server: str) -> 'DatabaseConfigBuilder':
        """Establece el servidor"""
        self._config['server'] = server
        return self
    
    def with_database(self, database: str) -> 'DatabaseConfigBuilder':
        """Establece la base de datos"""
        self._config['database'] = database
        return self
    
    def with_username(self, username: str) -> 'DatabaseConfigBuilder':
        """Establece el usuario"""
        self._config['username'] = username
        return self
    
    def with_secrets(self, secret_name: str, secret_key: str) -> 'DatabaseConfigBuilder':
        """Establece la configuración de secretos"""
        self._config['secret_name'] = secret_name
        self._config['secret_key'] = secret_key
        return self
    
    def with_port(self, port: int) -> 'DatabaseConfigBuilder':
        """Establece el puerto (opcional)"""
        self._config['port'] = port
        return self
    
    def from_dict(self, data: dict) -> 'DatabaseConfigBuilder':
        """
        Carga configuración desde un diccionario
        
        Args:
            data: Diccionario con los datos de configuración
            
        Returns:
            Self para chaining
        """
        # Mapear endpoint_name: ENDPOINT_NAME o endpoint_name
        if 'endpoint_name' in data:
            self.with_endpoint_name(data['endpoint_name'])
        elif 'ENDPOINT_NAME' in data:
            self.with_endpoint_name(data['ENDPOINT_NAME'])
        
        # Mapear db_type: BD_TYPE o db_type
        if 'db_type' in data:
            self.with_db_type(data['db_type'])
        elif 'BD_TYPE' in data:
            self.with_db_type(data['BD_TYPE'])
        
        # Mapear server: SRC_SERVER_NAME o server
        if 'server' in data:
            self.with_server(data['server'])
        elif 'SRC_SERVER_NAME' in data:
            self.with_server(data['SRC_SERVER_NAME'])
        # Mapear database: SRC_DB_NAME o SRC_DATABASE_NAME
        if 'database' in data:
            self.with_database(data['database'])
        elif 'SRC_DB_NAME' in data:
            self.with_database(data['SRC_DB_NAME'])
        elif 'SRC_DATABASE_NAME' in data:
            self.with_database(data['SRC_DATABASE_NAME'])
        
        # Mapear username: SRC_DB_USERNAME o SRC_USER_NAME
        if 'username' in data:
            self.with_username(data['username'])
        elif 'SRC_DB_USERNAME' in data:
            self.with_username(data['SRC_DB_USERNAME'])
        elif 'SRC_USER_NAME' in data:
            self.with_username(data['SRC_USER_NAME'])
        # Mapear secret_name y secret_key: SRC_DB_SECRET se usa para secret_key, SECRET_NAME para secret_name
        secret_name = None
        secret_key = None
        
        if 'secret_name' in data:
            secret_name = data['secret_name']
        elif 'SECRET_NAME' in data:
            secret_name = data['SECRET_NAME']
        
        if 'secret_key' in data:
            secret_key = data['secret_key']
        elif 'SRC_DB_SECRET' in data:
            secret_key = data['SRC_DB_SECRET']
        elif 'SECRET_KEY' in data:
            secret_key = data['SECRET_KEY']
        
        # Si no hay secret_key pero hay secret_name, usar 'password' como default
        if secret_key is None:
            secret_key = 'password'
        
        # Solo establecer secrets si tenemos al menos secret_key
        if secret_key or secret_name:
            if not secret_name:
                # Si no hay secret_name pero hay secret_key, usar secret_key como nombre
                secret_name = secret_key if secret_key else ''
            self.with_secrets(secret_name, secret_key)
        # Mapear port: DB_PORT_NUMBER, SRC_PORT, o port
        if 'port' in data:
            port = data['port']
            if port:
                self.with_port(int(port) if isinstance(port, str) else port)
        elif 'DB_PORT_NUMBER' in data:
            port = data['DB_PORT_NUMBER']
            if port:
                self.with_port(int(port) if isinstance(port, str) else port)
        elif 'SRC_PORT' in data:
            port = data['SRC_PORT']
            if port:
                self.with_port(int(port) if isinstance(port, str) else port)
        return self
    
    def build(self) -> DatabaseConfig:
        """
        Construye el DatabaseConfig
        
        Returns:
            Instancia de DatabaseConfig
            
        Raises:
            ValueError: Si faltan campos requeridos
        """
        required_fields = ['endpoint_name', 'db_type', 'server', 'database', 'username', 'secret_key']
        missing_fields = [field for field in required_fields if field not in self._config]
        
        if missing_fields:
            raise ValueError(
                f"Campos requeridos faltantes para DatabaseConfig: {missing_fields}"
            )
        
        # Validar que secret_name esté presente si secret_key está
        if 'secret_key' in self._config and 'secret_name' not in self._config:
            raise ValueError("secret_name es requerido cuando se especifica secret_key")
        
        return DatabaseConfig(
            endpoint_name=self._config['endpoint_name'],
            db_type=self._config['db_type'],
            server=self._config['server'],
            database=self._config['database'],
            username=self._config['username'],
            secret_key=self._config['secret_key'],
            secret_name=self._config.get('secret_name', ''),
            port=self._config.get('port')
        )
    
    @classmethod
    def create(cls) -> 'DatabaseConfigBuilder':
        """Factory method para crear un nuevo builder"""
        return cls()

