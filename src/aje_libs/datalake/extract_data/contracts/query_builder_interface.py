# -*- coding: utf-8 -*-
"""
Interfaz para Query Builders específicos por base de datos.
Permite desacoplar la generación de queries SQL de las estrategias de extracción.

Siguiendo el principio de Dependency Inversion (DIP):
- Las interfaces dependen de modelos compartidos (shared/models)
- No dependen de implementaciones específicas (strategies/)
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ...shared.models import TableConfig, ExtractionParams


class IQueryBuilder(ABC):
    """
    Interfaz para construir queries SQL específicas por base de datos.
    
    Cada implementación maneja las particularidades de su motor de base de datos:
    - Sintaxis de tipos de datos (DATETIME2 vs TIMESTAMP)
    - Paginación (TOP vs LIMIT)
    - Funciones de fecha/hora
    - Identificadores (brackets vs quotes)
    """
    
    def __init__(self, table_config: TableConfig):
        """
        Inicializa el query builder con la configuración de tabla.
        
        Args:
            table_config: Configuración de la tabla a extraer
        """
        self.table_config = table_config
    
    @abstractmethod
    def build_select_query(self, params: ExtractionParams) -> str:
        """
        Construye una query SELECT completa a partir de ExtractionParams.
        
        Args:
            params: Parámetros de extracción con columnas, filtros, etc.
            
        Returns:
            Query SQL completa como string
        """
        pass
    
    @abstractmethod
    def build_min_max_query(self, column: str, additional_where: Optional[str] = None) -> str:
        """
        Construye query para obtener valores MIN y MAX de una columna.
        
        Args:
            column: Nombre de la columna
            additional_where: Condiciones WHERE adicionales (opcional)
            
        Returns:
            Query SQL: SELECT MIN(column) as min_val, MAX(column) as max_val FROM ...
        """
        pass
    
    @abstractmethod
    def format_datetime_value(self, value: str, precision: int = 6) -> str:
        """
        Formatea un valor de fecha/hora para usar en queries SQL.
        
        Args:
            value: Valor de fecha como string
            precision: Precisión en microsegundos (default: 6)
            
        Returns:
            Valor formateado para SQL (ej: CAST('2025-01-01 12:00:00.000000' AS DATETIME2(6)))
        """
        pass
    
    @abstractmethod
    def format_datetime_comparison(self, column: str, value: str, operator: str = ">") -> str:
        """
        Construye una comparación de fecha/hora con casting apropiado.
        
        Args:
            column: Nombre de la columna
            value: Valor de fecha formateado
            operator: Operador de comparación (>, >=, <, <=, =)
            
        Returns:
            Condición SQL formateada (ej: CAST(column AS DATETIME2(6)) > CAST('...' AS DATETIME2(6)))
        """
        pass
    
    @abstractmethod
    def build_pagination_clause(self, limit: int, offset: Optional[int] = None) -> str:
        """
        Construye cláusula de paginación según el motor de base de datos.
        
        Args:
            limit: Número máximo de filas
            offset: Número de filas a saltar (opcional)
            
        Returns:
            Cláusula de paginación (ej: "TOP 100" para SQL Server, "LIMIT 100 OFFSET 0" para PostgreSQL)
        """
        pass
    
    @abstractmethod
    def build_chunked_query(self, base_query: str, order_by: str, offset: int, chunk_size: int) -> str:
        """
        Construye query paginada para chunking.
        
        Args:
            base_query: Query base sin paginación
            order_by: Columna para ordenar
            offset: Número de filas a saltar
            chunk_size: Tamaño del chunk
            
        Returns:
            Query con paginación aplicada
        """
        pass
    
    @abstractmethod
    def quote_identifier(self, identifier: str) -> str:
        """
        Aplica comillas/identificadores apropiados según el motor de base de datos.
        
        Args:
            identifier: Nombre de tabla, columna, etc.
            
        Returns:
            Identificador con comillas apropiadas (ej: [table] para SQL Server, "table" para PostgreSQL)
        """
        pass

