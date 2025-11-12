# load/log_storage/dynamodb_log_storage.py
from ....shared.contracts.logging import ILogStorage
from ....shared.services.logging import LoggerService
from typing import Optional, Dict, Any, List, Union
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from dataclasses import is_dataclass, asdict
import boto3


class DynamoDBLogStorage(ILogStorage):
    """Implementación DynamoDB para almacenamiento de logs"""
    def __init__(self, table_name: str, region: str = "us-east-1"):
        """
        Inicializa el storage de logs DynamoDB
        
        Args:
            table_name: Nombre de la tabla DynamoDB para logs
            region: Región AWS
        """
        self.logger = LoggerService.get_logger(__name__)
        self.table_name = table_name
        self.region = region
        
        # Usar boto3 directamente ya que la estructura de logs usa PROCESS_ID y DATE_SYSTEM como keys
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.dynamodb_table = self.dynamodb.Table(table_name) if table_name else None
            self.logger.debug(f"DynamoDBLogStorage inicializado - Tabla: {table_name}")
        except Exception as e:
            self.logger.error(f"Error inicializando DynamoDBLogStorage: {e}")
            self.dynamodb_table = None
    
    def store_log(self, log_entry: Dict[str, Any]) -> bool:
        """
        Implementación del contrato para almacenar logs.
        
        Args:
            log_entry: Diccionario con los datos del log.
        """
        return self.put_log(log_entry)
    
    def put_log(self, log_record: Dict[str, Any]) -> bool:
        """
        Inserta un registro de log en DynamoDB
        
        Args:
            log_record: Diccionario con los datos del log
            
        Returns:
            bool: True si se insertó correctamente
        """
        if not self.dynamodb_table:
            self.logger.warning("DynamoDB no configurado, log no registrado")
            return False
        
        try:
            # Sanitizar el registro para DynamoDB
            sanitized_record = self._sanitize_for_dynamodb(log_record)
            
            # Insertar en DynamoDB
            self.dynamodb_table.put_item(Item=sanitized_record)
            self.logger.debug(f"Log registrado en DynamoDB - PROCESS_ID: {log_record.get('PROCESS_ID', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registrando log en DynamoDB: {e}", exc_info=True)
            return False
    
    def get_logs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene logs según criterios de búsqueda
        
        Args:
            process_id: ID del proceso a buscar
            table_name: Nombre de la tabla a buscar
            limit: Límite de resultados
            
        Returns:
            Lista de registros de log
        """
        if filters is None:
            filters = {}

        # Compatibilidad con claves en mayúsculas/minúsculas
        process_id = filters.get('process_id') or filters.get('PROCESS_ID')
        table_name = filters.get('table_name') or filters.get('TABLE_NAME')

        return self._get_logs_by_filters(process_id, table_name, limit)

    # Compatibilidad hacia atrás para llamados antiguos que usen parámetros explícitos
    def get_logs_by_params(
        self,
        process_id: Optional[str] = None,
        table_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        return self._get_logs_by_filters(process_id, table_name, limit)

    def _get_logs_by_filters(
        self,
        process_id: Optional[str],
        table_name: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        if not self.dynamodb_table:
            self.logger.warning("DynamoDB no configurado, no se pueden obtener logs")
            return []
        
        try:
            # Construir filtros
            filter_parts = []
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            if process_id:
                filter_parts.append("#PROCESS_ID = :process_id")
                expression_attribute_names['#PROCESS_ID'] = 'PROCESS_ID'
                expression_attribute_values[':process_id'] = process_id
            
            if table_name:
                filter_parts.append("#TABLE_NAME = :table_name")
                expression_attribute_names['#TABLE_NAME'] = 'TABLE_NAME'
                expression_attribute_values[':table_name'] = table_name
            
            if not filter_parts:
                # Si no hay filtros, obtener todos (limitado)
                filter_expression = None
            else:
                filter_expression = " AND ".join(filter_parts)
            
            # Escanear tabla
            scan_kwargs = {'Limit': limit}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
                scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names
                scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            
            response = self.dynamodb_table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # Si hay más páginas, continuar escaneando
            while 'LastEvaluatedKey' in response and len(items) < limit:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = self.dynamodb_table.scan(**scan_kwargs)
                items.extend(response.get('Items', []))
                if len(items) >= limit:
                    break
            
            return items[:limit]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo logs de DynamoDB: {e}", exc_info=True)
            return []
    
    def delete_log(self, process_id: str, date_system: str) -> bool:
        """
        Elimina un log específico
        
        Args:
            process_id: ID del proceso
            date_system: Timestamp del log (DATE_SYSTEM)
            
        Returns:
            bool: True si se eliminó correctamente
        """
        if not self.dynamodb_table:
            self.logger.warning("DynamoDB no configurado, no se puede eliminar log")
            return False
        
        try:
            key = {
                'PROCESS_ID': process_id,
                'DATE_SYSTEM': date_system
            }
            
            self.dynamodb_table.delete_item(Key=key)
            self.logger.debug(f"Log eliminado - PROCESS_ID: {process_id}, DATE_SYSTEM: {date_system}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error eliminando log de DynamoDB: {e}", exc_info=True)
            return False
    
    def cleanup_table_logs(self, table_name: str, team: str = "", 
                          data_source: str = "", endpoint_name: str = "") -> Dict[str, Any]:
        """
        Limpia todos los logs relacionados con una tabla
        
        Args:
            table_name: Nombre de la tabla (STAGE_TABLE_NAME)
            team: Nombre del equipo (opcional, para construir PROCESS_ID)
            data_source: Fuente de datos (opcional)
            endpoint_name: Nombre del endpoint (opcional)
            
        Returns:
            Dict con resultado del cleanup:
            {
                'success': bool,
                'items_deleted': int,
                'details': str,
                'errors': List[str]
            }
        """
        result = {
            'success': False,
            'items_deleted': 0,
            'details': '',
            'errors': []
        }
        
        if not self.dynamodb_table:
            error_msg = "Tabla de logs no inicializada"
            result['errors'].append(error_msg)
            result['details'] = error_msg
            return result
        
        try:
            # Construir PROCESS_ID según formato de DynamoDBLogger
            # Formato: team-datasource-endpoint-table_name (en minúsculas)
            if team and data_source and endpoint_name:
                process_id_pattern = f"{team}-{data_source}-{endpoint_name}-{table_name}".lower()
            else:
                # Si no tenemos todos los parámetros, buscar solo por TABLE_NAME
                process_id_pattern = None
            
            self.logger.info(
                f"🧹 Limpiando logs - "
                f"DynamoDB table: {self.table_name}, "
                f"table_name (STAGE_TABLE_NAME): {table_name}, "
                f"team: {team or 'N/A'}, "
                f"data_source: {data_source or 'N/A'}, "
                f"endpoint_name: {endpoint_name or 'N/A'}, "
                f"process_id_pattern (buscará): {process_id_pattern or 'N/A (solo TABLE_NAME)'}"
            )
            # Escanear tabla buscando logs que coincidan
            deleted_count = 0
            items_to_delete = []
            
            try:
                # Construir filtro según lo que tengamos disponible
                if process_id_pattern:
                    # Buscar SOLO por PROCESS_ID (corregido)
                    self.logger.debug(f"Buscando logs con PROCESS_ID = '{process_id_pattern}'")
                    filter_expression = "#PROCESS_ID = :process_id"
                    expression_attribute_names = {
                        '#PROCESS_ID': 'PROCESS_ID'
                    }
                    expression_attribute_values = {
                        ':process_id': process_id_pattern
                    }
                else:
                    # Si no tenemos PROCESS_ID, buscar solo por TABLE_NAME
                    self.logger.debug(f"Buscando logs con TABLE_NAME = '{table_name}'")
                    filter_expression = "#TABLE_NAME = :table_name"
                    expression_attribute_names = {
                        '#TABLE_NAME': 'TABLE_NAME'
                    }
                    expression_attribute_values = {
                        ':table_name': table_name
                    }
                
                # 🔧 IMPORTANTE: DynamoDB scan con FilterExpression puede requerir múltiples páginas
                # El FilterExpression se aplica DESPUÉS del scan, así que debemos paginar correctamente
                items_to_delete = []
                page_count = 0
                
                # Primera página del scan
                scan_response = self.dynamodb_table.scan(
                    FilterExpression=filter_expression,
                    ExpressionAttributeNames=expression_attribute_names,
                    ExpressionAttributeValues=expression_attribute_values
                )
                
                items_to_delete.extend(scan_response.get('Items', []))
                page_count = 1
                
                # Continuar paginando si hay más resultados
                while 'LastEvaluatedKey' in scan_response:
                    page_count += 1
                    scan_response = self.dynamodb_table.scan(
                        FilterExpression=filter_expression,
                        ExpressionAttributeNames=expression_attribute_names,
                        ExpressionAttributeValues=expression_attribute_values,
                        ExclusiveStartKey=scan_response['LastEvaluatedKey']
                    )
                    page_items = scan_response.get('Items', [])
                    items_to_delete.extend(page_items)
                
                # Resumir búsqueda
                if page_count > 1:
                    self.logger.debug(f"Búsqueda completada: {len(items_to_delete)} items en {page_count} páginas")
                
                if not items_to_delete:
                    self.logger.info(f"✅ No se encontraron logs para limpiar")
                    result['success'] = True
                    result['details'] = "No se encontraron logs"
                    return result
                
                self.logger.info(f"📦 Encontrados {len(items_to_delete)} logs para eliminar")
                
                # Eliminar cada item (resumir progreso cada 10 items)
                for idx, item in enumerate(items_to_delete, 1):
                    try:
                        # Extraer keys y convertir tipos correctamente (DynamoDB puede devolver Decimal, etc.)
                        process_id_raw = item.get('PROCESS_ID')
                        date_system_raw = item.get('DATE_SYSTEM')
                        
                        # Convertir tipos correctamente para DynamoDB
                        process_id = None
                        date_system = None
                        
                        if process_id_raw is not None:
                            if isinstance(process_id_raw, Decimal):
                                process_id = str(process_id_raw)
                            elif isinstance(process_id_raw, str):
                                process_id = process_id_raw
                            else:
                                process_id = str(process_id_raw)
                        
                        if date_system_raw is not None:
                            if isinstance(date_system_raw, Decimal):
                                date_system = str(date_system_raw)
                            elif isinstance(date_system_raw, str):
                                date_system = date_system_raw
                            else:
                                date_system = str(date_system_raw)
                        
                        # Verificar que tenemos las keys necesarias
                        if not process_id or not date_system:
                            self.logger.warning(
                                f"⚠️ No se pudo determinar keys para eliminar log - "
                                f"PROCESS_ID: {process_id}, DATE_SYSTEM: {date_system}"
                            )
                            continue
                        
                        # Construir key para delete_item
                        key_to_delete = {
                            'PROCESS_ID': process_id,
                            'DATE_SYSTEM': date_system
                        }
                        
                        try:
                            response = self.dynamodb_table.delete_item(
                                Key=key_to_delete,
                                ReturnValues='ALL_OLD'
                            )
                            
                            # Verificar que se eliminó
                            if response.get('Attributes'):
                                deleted_count += 1
                                # Solo loguear progreso cada 10 items o al final
                                if idx % 10 == 0 or idx == len(items_to_delete):
                                    self.logger.debug(f"Eliminados {deleted_count}/{idx} logs")
                            else:
                                self.logger.debug(f"Log no encontrado: {process_id}")
                        except Exception as delete_error:
                            self.logger.error(
                                f"❌ Error en delete_item - "
                                f"PROCESS_ID: {process_id}, DATE_SYSTEM: {date_system}, "
                                f"Error: {str(delete_error)}",
                                exc_info=True
                            )
                            raise  # Re-lanzar para que se capture en el except externo
                            
                    except Exception as e:
                        error_msg = (
                            f"❌ Error eliminando log - "
                            f"PROCESS_ID: {item.get('PROCESS_ID', 'unknown')}, "
                            f"DATE_SYSTEM: {item.get('DATE_SYSTEM', 'unknown')}, "
                            f"Error: {str(e)}"
                        )
                        result['errors'].append(error_msg)
                        self.logger.error(error_msg, exc_info=True)
                
            except Exception as e:
                # Si el scan falla por estructura de tabla diferente
                error_msg = f"No se pudo completar limpieza de logs: {str(e)}"
                result['errors'].append(error_msg)
                self.logger.error(error_msg)
            
            result['success'] = deleted_count > 0 or len(items_to_delete) == 0
            result['items_deleted'] = deleted_count
            result['details'] = f"Eliminados {deleted_count} logs de {len(items_to_delete)} encontrados"
            
            if deleted_count == len(items_to_delete):
                self.logger.info(
                    f"✅ Limpieza de logs completada exitosamente - "
                    f"{deleted_count} de {len(items_to_delete)} eliminados"
                )
            elif deleted_count > 0:
                self.logger.warning(
                    f"⚠️ Limpieza de logs parcial - "
                    f"{deleted_count} de {len(items_to_delete)} eliminados. "
                    f"Revisar errores en logs."
                )
            else:
                self.logger.warning(
                    f"⚠️ No se eliminaron logs - "
                    f"0 de {len(items_to_delete)} eliminados. "
                    f"Revisar errores en logs."
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Error durante limpieza de logs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)
            result['details'] = error_msg
            return result
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Cumple con el contrato limpiando logs antiguos basados en DATE_SYSTEM.
        
        Args:
            days_to_keep: Cantidad de días a conservar.
        
        Returns:
            Número de registros eliminados.
        """
        if not self.dynamodb_table:
            self.logger.warning("DynamoDB no configurado, no se pueden limpiar logs antiguos")
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        deleted_count = 0

        try:
            scan_kwargs = {
                'ProjectionExpression': 'PROCESS_ID, DATE_SYSTEM'
            }
            response = self.dynamodb_table.scan(**scan_kwargs)
            items = response.get('Items', [])

            def _parse_date(date_value: Union[str, Decimal]) -> Optional[datetime]:
                if isinstance(date_value, Decimal):
                    # Asumir que viene como timestamp en segundos
                    return datetime.fromtimestamp(float(date_value), tz=timezone.utc)
                if isinstance(date_value, str):
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
                        try:
                            return datetime.strptime(date_value, fmt).replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                return None

            while True:
                for item in items:
                    process_id = item.get('PROCESS_ID')
                    date_value = item.get('DATE_SYSTEM')
                    log_datetime = _parse_date(date_value)

                    if not process_id or not log_datetime:
                        continue

                    if log_datetime < cutoff:
                        try:
                            self.dynamodb_table.delete_item(
                                Key={
                                    'PROCESS_ID': process_id,
                                    'DATE_SYSTEM': date_value
                                }
                            )
                            deleted_count += 1
                        except Exception as delete_error:
                            self.logger.error(
                                f"Error eliminando log antiguo de DynamoDB: {delete_error}",
                                exc_info=True
                            )

                last_evaluated_key = response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break

                response = self.dynamodb_table.scan(
                    ExclusiveStartKey=last_evaluated_key,
                    **scan_kwargs
                )
                items = response.get('Items', [])

        except Exception as e:
            self.logger.error(f"Error durante cleanup_old_logs: {e}", exc_info=True)
            return deleted_count

        self.logger.info(f"cleanup_old_logs eliminó {deleted_count} registros antiguos de DynamoDB")
        return deleted_count
    
    def _sanitize_for_dynamodb(self, obj: Any) -> Any:
        """
        Sanitiza objetos para DynamoDB convirtiendo tipos no soportados.
        
        - float -> Decimal
        - inf/nan -> None
        - Recursivo para dict y list
        """
        from decimal import Decimal
        
        if obj is None:
            return None

        if is_dataclass(obj):
            return self._sanitize_for_dynamodb(asdict(obj))

        if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
            try:
                return self._sanitize_for_dynamodb(obj.to_dict())
            except Exception:
                return str(obj)

        if hasattr(obj, "__dict__") and not isinstance(obj, (str, bytes, bytearray, bool, int, float, Decimal)):
            return self._sanitize_for_dynamodb(vars(obj))

        if isinstance(obj, dict):
            return {k: self._sanitize_for_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_for_dynamodb(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, float):
            # Manejar casos especiales
            if obj != obj or obj == float('inf') or obj == float('-inf'):
                return None
            return Decimal(str(obj))
        elif isinstance(obj, set):
            return {self._sanitize_for_dynamodb(item) for item in obj if item is not None}
        return obj

