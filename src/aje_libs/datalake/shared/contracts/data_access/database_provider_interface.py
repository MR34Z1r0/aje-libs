# -*- coding: utf-8 -*-
"""
Interface para proveedores de bases de datos NoSQL (DIP - Dependency Inversion Principle)
Abstrae DynamoDB, MongoDB, Cassandra, etc.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class IDatabaseProvider(ABC):
    """Interface para proveedores de bases de datos NoSQL (abstrae DynamoDB, MongoDB, etc.)"""
    
    @abstractmethod
    def get_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un item por su clave primaria
        
        Args:
            partition_key: Valor de la clave de partición
            sort_key: Valor de la clave de ordenamiento (opcional)
            
        Returns:
            Dict con el item o None si no existe
        """
        pass
    
    @abstractmethod
    def put_item(
        self,
        item: Dict[str, Any],
        condition: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inserta o actualiza un item
        
        Args:
            item: Diccionario con los datos del item
            condition: Expresión de condición opcional
            
        Returns:
            Respuesta del proveedor
        """
        pass
    
    @abstractmethod
    def update_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None,
        update_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Actualiza un item existente
        
        Args:
            partition_key: Valor de la clave de partición
            sort_key: Valor de la clave de ordenamiento (opcional)
            update_expression: Expresión de actualización (ej: 'SET ATTR = :val')
            expression_attribute_values: Valores para la expresión de actualización
            condition_expression: Expresión de condición opcional
            
        Returns:
            Respuesta del proveedor
        """
        pass
    
    @abstractmethod
    def delete_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Elimina un item
        
        Args:
            partition_key: Valor de la clave de partición
            sort_key: Valor de la clave de ordenamiento (opcional)
            condition_expression: Expresión de condición opcional
            
        Returns:
            Respuesta del proveedor
        """
        pass
    
    @abstractmethod
    def query_table(
        self,
        key_condition: str,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
        filter_expression: Optional[str] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Consulta items usando una clave
        
        Args:
            key_condition: Condición de clave (ej: 'PK = :pk')
            expression_attribute_values: Valores para la expresión
            limit: Límite de resultados (opcional)
            scan_forward: Orden de consulta (True = ascendente, False = descendente)
            filter_expression: Expresión de filtro adicional (opcional)
            expression_attribute_names: Nombres de atributos para expresiones (opcional)
            
        Returns:
            Lista de items encontrados
        """
        pass
    
    @abstractmethod
    def scan_table(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Escanea la tabla completa (menos eficiente que query)
        
        Args:
            filter_expression: Expresión de filtro (opcional)
            expression_attribute_values: Valores para la expresión
            limit: Límite de resultados (opcional)
            
        Returns:
            Lista de items encontrados
        """
        pass

