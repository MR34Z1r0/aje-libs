# -*- coding: utf-8 -*-
"""
Query Builder específico para SQL Server.
Maneja sintaxis específica de SQL Server como DATETIME2, TOP, brackets, etc.
"""
from typing import Optional
from ...contracts.query_builder_interface import IQueryBuilder
from ....shared.models import TableConfig, ExtractionParams  # ✅ ExtractionParams desde shared/models


class SQLServerQueryBuilder(IQueryBuilder):
    """Query Builder para SQL Server"""
    
    def build_select_query(self, params: ExtractionParams) -> str:
        """Construye query SELECT para SQL Server"""
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
        
        # Paginación: SQL Server usa TOP o OFFSET/FETCH
        if params.limit:
            if params.order_by:
                # Si hay ORDER BY, usar OFFSET/FETCH (SQL Server 2012+)
                query += f" OFFSET 0 ROWS FETCH NEXT {params.limit} ROWS ONLY"
            else:
                # Sin ORDER BY, usar TOP
                query = query.replace("SELECT ", f"SELECT TOP {params.limit} ", 1)
        
        return query
    
    def build_min_max_query(self, column: str, additional_where: Optional[str] = None) -> str:
        """Construye query MIN/MAX para SQL Server"""
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
        """Formatea valor datetime para SQL Server usando DATETIME2"""
        return f"CAST('{value}' AS DATETIME2({precision}))"
    
    def format_datetime_comparison(self, column: str, value: str, operator: str = ">") -> str:
        """Construye comparación datetime con casting apropiado para SQL Server"""
        formatted_value = self.format_datetime_value(value)
        return f"CAST({column} AS DATETIME2(6)) {operator} {formatted_value}"
    
    def build_pagination_clause(self, limit: int, offset: Optional[int] = None) -> str:
        """Construye cláusula de paginación para SQL Server"""
        if offset is not None:
            # SQL Server 2012+ usa OFFSET/FETCH (requiere ORDER BY)
            return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
        else:
            # Sin offset, usar TOP
            return f"TOP {limit}"
    
    def build_chunked_query(self, base_query: str, order_by: str, offset: int, chunk_size: int) -> str:
        """Construye query paginada para chunking en SQL Server"""
        # Asegurar que hay ORDER BY (requerido para OFFSET/FETCH)
        if "ORDER BY" not in base_query.upper():
            base_query += f" ORDER BY {order_by}"
        
        # Agregar paginación
        pagination = self.build_pagination_clause(chunk_size, offset)
        return f"{base_query} {pagination}"
    
    def quote_identifier(self, identifier: str) -> str:
        """Aplica brackets para SQL Server"""
        # SQL Server usa brackets [identifier]
        # Si ya tiene brackets o comillas, no duplicar
        if identifier.startswith('[') and identifier.endswith(']'):
            return identifier
        if identifier.startswith('"') and identifier.endswith('"'):
            return identifier
        return f"[{identifier}]"
    
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

