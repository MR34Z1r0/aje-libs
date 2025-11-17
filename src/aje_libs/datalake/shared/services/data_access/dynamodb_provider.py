# -*- coding: utf-8 -*-
"""
Implementación de IDatabaseProvider usando AWS DynamoDB (DIP - Dependency Inversion)
"""
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError

from ...contracts.data_access import IDatabaseProvider
from ...services.logging import LoggerService
from aje_libs.common.aws.core import handle_aws_error, is_retryable_error  # ✅ Manejo de errores mejorado

# ✅ DIP: Importar DynamoDBHelper solo para compatibilidad, idealmente debería ser inyectado
from aje_libs.common.aws.helpers.dynamodb_helper import DynamoDBHelper


class DynamoDBProvider(IDatabaseProvider):
    """Implementación de IDatabaseProvider para AWS DynamoDB"""
    
    def __init__(
        self,
        table_name: str,
        pk_name: str,
        sk_name: Optional[str] = None,
        region: Optional[str] = None,
        logger_name: Optional[str] = None
    ):
        """
        Inicializa el proveedor de base de datos DynamoDB
        
        Args:
            table_name: Nombre de la tabla DynamoDB
            pk_name: Nombre de la clave de partición
            sk_name: Nombre de la clave de ordenamiento (opcional)
            region: Región de AWS (opcional)
            logger_name: Nombre del logger (opcional)
        """
        self.table_name = table_name
        self.pk_name = pk_name
        self.sk_name = sk_name
        self.region = region
        self.logger = LoggerService.get_logger(logger_name or __name__)
        
        # ✅ DIP: Usar DynamoDBHelper internamente (paso intermedio)
        # En el futuro, podríamos inyectar IDatabaseProvider directamente
        self._dynamo_helper = DynamoDBHelper(
            table_name=table_name,
            pk_name=pk_name,
            sk_name=sk_name,
            region_name=region
        )
    
    def get_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Obtiene un item por su clave primaria"""
        try:
            return self._dynamo_helper.get_item(partition_key, sort_key)
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"obtener item de DynamoDB (table={self.table_name}, PK={partition_key}, SK={sort_key})", self.logger)
            raise
    
    def put_item(
        self,
        item: Dict[str, Any],
        condition: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inserta o actualiza un item"""
        try:
            return self._dynamo_helper.put_item(item, condition)
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            # No loguear el item completo para evitar exponer datos sensibles
            handle_aws_error(e, f"insertar item en DynamoDB (table={self.table_name})", self.logger)
            raise
    
    def update_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None,
        update_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza un item existente"""
        try:
            return self._dynamo_helper.update_item(
                partition_key=partition_key,
                sort_key=sort_key,
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values,
                condition_expression=condition_expression
            )
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"actualizar item en DynamoDB (table={self.table_name}, PK={partition_key}, SK={sort_key})", self.logger)
            raise
    
    def delete_item(
        self,
        partition_key: str,
        sort_key: Optional[str] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Elimina un item"""
        try:
            return self._dynamo_helper.delete_item(
                partition_key=partition_key,
                sort_key=sort_key,
                condition_expression=condition_expression
            )
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"eliminar item de DynamoDB (table={self.table_name}, PK={partition_key}, SK={sort_key})", self.logger)
            raise
    
    def query_table(
        self,
        key_condition: str,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
        filter_expression: Optional[str] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Consulta items usando una clave"""
        try:
            # DynamoDBHelper.query_table espera parámetros adicionales opcionales
            return self._dynamo_helper.query_table(
                key_condition=key_condition,
                filter_expression=filter_expression,
                expression_attribute_values=expression_attribute_values,
                expression_attribute_names=expression_attribute_names,
                limit=limit,
                scan_forward=scan_forward
            )
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"consultar tabla DynamoDB (table={self.table_name}, key_condition={key_condition})", self.logger)
            raise
    
    def scan_table(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Escanea la tabla completa (menos eficiente que query)"""
        try:
            return self._dynamo_helper.scan_table(
                filter_expression=filter_expression,
                expression_attribute_values=expression_attribute_values,
                expression_attribute_names=expression_attribute_names,
                limit=limit
            )
        except ClientError as e:
            # ✅ Manejo mejorado de errores de AWS
            handle_aws_error(e, f"escanear tabla DynamoDB (table={self.table_name})", self.logger)
            raise

