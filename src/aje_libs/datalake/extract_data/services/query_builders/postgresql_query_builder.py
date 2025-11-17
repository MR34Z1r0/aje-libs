# -*- coding: utf-8 -*-
"""
Query Builder específico para PostgreSQL.
Maneja sintaxis específica de PostgreSQL como TIMESTAMP, LIMIT/OFFSET, quotes, etc.
"""
from typing import Optional
from ...contracts.query_builder_interface import IQueryBuilder
from ....shared.models import TableConfig, ExtractionParams  # ✅ ExtractionParams desde shared/models


class PostgreSQLQueryBuilder(IQueryBuilder):
    """Query Builder para PostgreSQL"""
    
    def build_select_query(self, params: ExtractionParams) -> str:
        """Construye query SELECT para PostgreSQL"""
        # SELECT clause
        columns_str = ', '.join(params.columns) if params.columns != ['*'] else '*'
        
        # FROM clause
        table_name = params.table_name
        
        # Construir query base
        query = f"SELECT {columns_str} FROM {table_name}"
        
        # WHERE clause
        where_clause = params.get_where_clause()
        if where_clause:
            query += f" WHERE {where_clause}"
        
        # ORDER BY clause
        if params.order_by:
            query += f" ORDER BY {params.order_by}"
        
        # Paginación: PostgreSQL usa LIMIT/OFFSET
        if params.limit:
            query += f" LIMIT {params.limit}"
            # PostgreSQL también soporta OFFSET si se necesita
        
        return query
    
    def build_min_max_query(self, column: str, additional_where: Optional[str] = None) -> str:
        """Construye query MIN/MAX para PostgreSQL"""
        # Construir FROM clause
        from_clause = self._build_from_clause()
        
        query = f"SELECT MIN({column}) as min_val, MAX({column}) as max_val FROM {from_clause}"
        
        # Agregar JOINs si existen
        if hasattr(self.table_config, 'join_expr') and self.table_config.join_expr and self.table_config.join_expr.strip():
            query += f" {self.table_config.join_expr.strip()}"
        
        where_conditions = [f"{column} <> 0"]
        
        # Agregar filtros adicionales
        if additional_where:
            where_conditions.append(additional_where)
        
        # Agregar FILTER_EXP si existe
        if hasattr(self.table_config, 'filter_exp') and self.table_config.filter_exp:
            clean_filter = self.table_config.filter_exp.replace('"', '').strip()
            if clean_filter:
                where_conditions.append(f"({clean_filter})")
        
        if where_conditions:
            query += f" WHERE {' AND '.join(where_conditions)}"
        
        return query
    
    def format_datetime_value(self, value: str, precision: int = 6) -> str:
        """Formatea valor datetime para PostgreSQL usando TIMESTAMP"""
        # PostgreSQL usa TIMESTAMP con precisión
        if precision > 0:
            return f"'{value}'::TIMESTAMP({precision})"
        else:
            return f"'{value}'::TIMESTAMP"
    
    def format_datetime_comparison(self, column: str, value: str, operator: str = ">") -> str:
        """Construye comparación datetime con casting apropiado para PostgreSQL"""
        formatted_value = self.format_datetime_value(value)
        return f"{column}::TIMESTAMP(6) {operator} {formatted_value}"
    
    def build_pagination_clause(self, limit: int, offset: Optional[int] = None) -> str:
        """Construye cláusula de paginación para PostgreSQL"""
        if offset is not None:
            return f"LIMIT {limit} OFFSET {offset}"
        else:
            return f"LIMIT {limit}"
    
    def build_chunked_query(self, base_query: str, order_by: str, offset: int, chunk_size: int) -> str:
        """Construye query paginada para chunking en PostgreSQL"""
        # Asegurar que hay ORDER BY (buena práctica para paginación)
        if "ORDER BY" not in base_query.upper():
            base_query += f" ORDER BY {order_by}"
        
        # Agregar paginación
        pagination = self.build_pagination_clause(chunk_size, offset)
        return f"{base_query} {pagination}"
    
    def quote_identifier(self, identifier: str) -> str:
        """Aplica comillas dobles para PostgreSQL"""
        # PostgreSQL usa comillas dobles "identifier"
        # Si ya tiene comillas, no duplicar
        if identifier.startswith('"') and identifier.endswith('"'):
            return identifier
        if identifier.startswith('[') and identifier.endswith(']'):
            # Convertir brackets a quotes
            return f'"{identifier[1:-1]}"'
        return f'"{identifier}"'
    
    def _build_from_clause(self) -> str:
        """Construye FROM clause con schema y tabla"""
        source_table = self.table_config.source_table or ""
        source_schema = self.table_config.source_schema or ""
        
        if '.' in source_table and not source_schema:
            return source_table.strip()
        elif source_schema:
            return f"{source_schema}.{source_table}".strip()
        else:
            return source_table.strip()

