"""
Helper para watermarks en DynamoDB.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Optional

import boto3
import pytz
from dateutil.relativedelta import relativedelta

from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger
from aje_libs.datalake.shared.models.watermark_status import WatermarkStatus

TZ_LIMA = pytz.timezone('America/Lima')


class DynamoDBWatermarkHelper:
    """Helper simplificado para operaciones de watermark en DynamoDB"""

    def __init__(self, table_name: str, team: str, data_source: str, endpoint_name: str, project_name: str = 'datalake', logger=None):
        self.table_name = table_name
        self.team = (team or '').strip()
        self.data_source = (data_source or '').strip()
        self.endpoint_name = (endpoint_name or '').strip()
        self.project_name = (project_name or 'datalake').strip()
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def _build_watermark_key(self, table_name: str, column_name: str) -> str:
        return f"{self.team}#{self.data_source}#{self.endpoint_name}#{(table_name or '').lower()}#{(column_name or '').lower()}"

    def get_last_pending_watermark(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        try:
            table_name_normalized = table_name.lower()
            column_name_normalized = column_name.lower()
            watermark_key = self._build_watermark_key(table_name_normalized, column_name_normalized)

            self.logger.info(
                f"🔍 Buscando watermark PENDING con clave: '{watermark_key}' "
                f"(team={self.team}, data_source={self.data_source}, endpoint_name={self.endpoint_name}, table_name={table_name}→{table_name_normalized}, "
                f"column_name={column_name}→{column_name_normalized})"
            )

            response = self.table.query(
                KeyConditionExpression="WATERMARK_KEY = :pk",
                ExpressionAttributeValues={':pk': watermark_key},
                ScanIndexForward=False
            )

            items_count = len(response.get('Items', []))
            self.logger.info(f"🔍 Query retornó {items_count} items con WATERMARK_KEY='{watermark_key}'")

            for idx, item in enumerate(response.get('Items', [])):
                metadata_str = item.get('METADATA', '{}')
                item_watermark_key = item.get('WATERMARK_KEY')
                item_table_name = item.get('TABLE_NAME')
                item_column_name = item.get('COLUMN_NAME')

                self.logger.info(
                    f"🔍 Item #{idx}: WATERMARK_KEY='{item_watermark_key}', "
                    f"TABLE_NAME='{item_table_name}', COLUMN_NAME='{item_column_name}'"
                )

                try:
                    metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    status = metadata.get('status')
                    self.logger.info(f"🔍 Item #{idx} status: '{status}'")

                    if status == WatermarkStatus.PENDING.value:
                        self.logger.info(
                            f"✅ Encontrado watermark PENDING: {item_watermark_key} "
                            f"(TIMESTAMP: {item.get('TIMESTAMP')}, EXTRACTED_VALUE: {item.get('EXTRACTED_VALUE')})"
                        )
                        return {
                            'watermark_key': item.get('WATERMARK_KEY'),
                            'timestamp': item.get('TIMESTAMP'),
                            'extracted_value': item.get('EXTRACTED_VALUE'),
                            'table_name': item.get('TABLE_NAME'),
                            'column_name': item.get('COLUMN_NAME').lower(),
                            'metadata': metadata
                        }
                except (json.JSONDecodeError, TypeError) as exc:
                    self.logger.warning(f"⚠️ Error parseando METADATA del item #{idx}: {exc}")
                    continue

            self.logger.warning(
                f"⚠️ No se encontró watermark PENDING con clave '{watermark_key}'. "
                f"Se encontraron {items_count} items pero ninguno con status PENDING"
            )
            return None

        except Exception as exc:
            self.logger.error(f"Error obteniendo watermark PENDING: {exc}", exc_info=True)
            return None

    def confirm_watermark(self, table_name: str, column_name: str, timestamp: str, additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            table_name_normalized = table_name.lower()
            column_name_normalized = column_name.lower()
            watermark_key = self._build_watermark_key(table_name_normalized, column_name_normalized)

            response = self.table.get_item(
                Key={
                    'WATERMARK_KEY': watermark_key,
                    'TIMESTAMP': timestamp
                }
            )

            if 'Item' not in response:
                self.logger.warning(
                    f"No se encontró watermark con TIMESTAMP {timestamp} para {table_name}.{column_name}"
                )
                return False

            item = response['Item']

            metadata_str = item.get('METADATA', '{}')
            try:
                existing_metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
            except (json.JSONDecodeError, TypeError):
                existing_metadata = {}

            if existing_metadata.get('status') != WatermarkStatus.PENDING.value:
                self.logger.warning(
                    f"Watermark no está en estado PENDING (status: {existing_metadata.get('status')}) "
                    f"para {table_name}.{column_name}"
                )
                return False

            confirmed_metadata = {
                **existing_metadata,
                'status': WatermarkStatus.CONFIRMED.value,
                'confirmed_at': dt.datetime.now(TZ_LIMA).isoformat(),
                'confirmed_by': 'light_transform',
                **(additional_metadata or {})
            }

            now = dt.datetime.now(TZ_LIMA)
            ttl_value = int((now + relativedelta(days=90)).timestamp())

            update_expression = (
                "SET #metadata = :metadata, "
                "#table_name = :table_name, "
                "#column_name = :column_name, "
                "#extracted_value = :extracted_value, "
                "#project_name = :project_name, "
                "#ttl = :ttl"
            )

            expression_attribute_names = {
                '#metadata': 'METADATA',
                '#table_name': 'TABLE_NAME',
                '#column_name': 'COLUMN_NAME',
                '#extracted_value': 'EXTRACTED_VALUE',
                '#project_name': 'PROJECT_NAME',
                '#ttl': 'TTL'
            }

            expression_attribute_values = {
                ':metadata': json.dumps(confirmed_metadata),
                ':table_name': table_name,
                ':column_name': column_name,
                ':extracted_value': item.get('EXTRACTED_VALUE'),
                ':project_name': self.project_name,
                ':ttl': ttl_value
            }

            self.table.update_item(
                Key={
                    'WATERMARK_KEY': watermark_key,
                    'TIMESTAMP': timestamp
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            self.logger.info(
                f"✅ Watermark confirmado: {table_name}.{column_name} = {item.get('EXTRACTED_VALUE')} "
                f"(TIMESTAMP: {timestamp})"
            )
            return True

        except Exception as exc:
            self.logger.error(f"Error confirmando watermark: {exc}", exc_info=True)
            return False

    def delete_watermarks(self, table_name: str, column_name: str) -> int:
        """Elimina todos los watermarks asociados a una tabla/columna."""
        try:
            table_name_normalized = table_name.lower()
            column_name_normalized = column_name.lower()
            watermark_key = self._build_watermark_key(table_name_normalized, column_name_normalized)

            self.logger.info(
                f"🧹 Eliminando watermarks con clave '{watermark_key}' en tabla {self.table_name}"
            )

            total_deleted = 0
            query_kwargs = {
                'KeyConditionExpression': "WATERMARK_KEY = :pk",
                'ExpressionAttributeValues': {':pk': watermark_key},
            }

            while True:
                response = self.table.query(**query_kwargs)
                items = response.get('Items', [])

                if not items:
                    break

                for item in items:
                    timestamp = item.get('TIMESTAMP')
                    if not timestamp:
                        continue
                    self.table.delete_item(
                        Key={
                            'WATERMARK_KEY': watermark_key,
                            'TIMESTAMP': timestamp
                        }
                    )
                    total_deleted += 1

                last_evaluated = response.get('LastEvaluatedKey')
                if not last_evaluated:
                    break
                query_kwargs['ExclusiveStartKey'] = last_evaluated

            self.logger.info(
                f"✅ Watermarks eliminados: {total_deleted} registros para {table_name}.{column_name}"
            )
            return total_deleted

        except Exception as exc:
            self.logger.error(f"Error eliminando watermarks para {table_name}.{column_name}: {exc}", exc_info=True)
            return 0


__all__ = ["DynamoDBWatermarkHelper"]

