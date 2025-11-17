# -*- coding: utf-8 -*-
"""
Modelo de datos para parámetros de extracción.

Este modelo es compartido entre múltiples capas:
- Strategies: Construyen ExtractionParams
- QueryBuilders: Reciben ExtractionParams para construir SQL
- Adapters: Transforman ExtractionParams en queries

Ubicado en shared/models para evitar dependencias circulares y seguir
el principio de Dependency Inversion (DIP) de SOLID.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ExtractionParams:
    """
    Parámetros unificados para todas las estrategias de extracción.
    
    Este es un DTO (Data Transfer Object) que encapsula todos los parámetros
    necesarios para construir una query SQL, independientemente del motor de
    base de datos o la estrategia de extracción.
    
    Attributes:
        table_name: Nombre completo de la tabla (puede incluir schema y alias)
        columns: Lista de columnas a seleccionar
        where_conditions: Lista de condiciones WHERE
        order_by: Columna para ordenar resultados
        limit: Límite de filas a retornar
        chunk_size: Tamaño de chunk para procesamiento paginado
        chunk_column: Columna para ordenar en chunking
        metadata: Metadatos adicionales (watermarks, particionado, etc.)
    """
    
    # Básicos
    table_name: str
    columns: List[str]
    
    # Filtros
    where_conditions: List[str] = field(default_factory=list)
    
    # Ordenamiento y paginación
    order_by: Optional[str] = None
    limit: Optional[int] = None
    
    # Chunking
    chunk_size: Optional[int] = None
    chunk_column: Optional[str] = None
    
    # Metadatos
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validaciones básicas después de inicialización"""
        if not self.table_name:
            raise ValueError("table_name es requerido")
        
        if not self.columns:
            self.columns = ['*']
        
        # Limpiar condiciones vacías
        self.where_conditions = [cond for cond in self.where_conditions if cond and cond.strip()]
    
    def add_where_condition(self, condition: str):
        """
        Agrega una condición WHERE.
        
        Args:
            condition: Condición SQL a agregar (ej: "column > 'value'")
        """
        if condition and condition.strip():
            self.where_conditions.append(condition.strip())
    
    def get_where_clause(self) -> Optional[str]:
        """
        Retorna la cláusula WHERE completa o None.
        
        Returns:
            String con todas las condiciones unidas por AND, o None si no hay condiciones
        """
        if not self.where_conditions:
            return None
        return " AND ".join(self.where_conditions)
    
    def get_columns_string(self) -> str:
        """
        Retorna las columnas como string para SQL.
        
        Returns:
            String con columnas separadas por comas, o '*' si está vacío
        """
        if not self.columns:
            return '*'
        
        # Si ya es una lista, unir con comas
        if isinstance(self.columns, list):
            if self.columns == ['*']:
                return '*'
            return ', '.join(self.columns)
        
        # Si es string, retornar tal como está
        return self.columns

