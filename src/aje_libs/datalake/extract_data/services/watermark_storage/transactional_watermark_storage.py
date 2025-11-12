# load/watermark_storage/transactional_watermark_storage.py
from ....shared.contracts.watermark import IWatermarkStorage
from ....shared.services.logging import LoggerService
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json

class WatermarkStatus(Enum):
    """Estados de watermark"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ROLLBACK = "ROLLBACK"

class TransactionalWatermarkStorage(IWatermarkStorage):
    """Wrapper transaccional sobre WatermarkStorage"""
    
    def __init__(self, base_storage: IWatermarkStorage, project_name: str, team: str = '', data_source: str = '', endpoint_name: str = ''):
        self.logger = LoggerService.get_logger(__name__)
        self.base_storage = base_storage
        self.project_name = project_name
        self.team = (team or '').strip()
        self.data_source = (data_source or '').strip()
        self.endpoint_name = (endpoint_name or '').strip()
        self._pending_watermarks = {}
        self.logger.info("✅ TransactionalWatermarkStorage initialized")

    def _build_watermark_key(self, table_name: str, column_name: str) -> str:
        table_norm = (table_name or '').lower()
        column_norm = (column_name or '').lower()
        return f"{self.team}#{self.data_source}#{self.endpoint_name}#{table_norm}#{column_norm}"
    
    def get_last_extracted_value(self, table_name: str, column_name: str) -> Optional[str]:
        """
        Obtiene el último watermark CONFIRMADO entre todos los registros.
        Solo busca CONFIRMED - ignora PENDING completamente.
        Si no hay CONFIRMED, retorna None (se hará full incremental).
        """
        try:
            history = self.base_storage.get_extraction_history(table_name, limit=50)
            
            confirmed_entry = None
            confirmed_timestamp = None
            
            # Iterar todos los registros para encontrar el CONFIRMED más reciente
            # ✅ Normalizar nombres a minúsculas para comparación (coincide con cómo se guarda)
            column_name_normalized = column_name.lower()
            for entry in history:
                entry_column = entry.get('column_name', '').lower()
                if entry_column == column_name_normalized:
                    metadata = entry.get('metadata', {})
                    status = metadata.get('status', 'CONFIRMED')
                    timestamp = entry.get('timestamp')
                    
                    # ✅ SOLO buscar CONFIRMED - ignorar PENDING
                    if status == WatermarkStatus.CONFIRMED.value:
                        # Guardar el CONFIRMED más reciente (mayor timestamp)
                        if confirmed_timestamp is None or timestamp > confirmed_timestamp:
                            confirmed_entry = entry
                            confirmed_timestamp = timestamp
            
            # Solo retornar si hay CONFIRMED
            if confirmed_entry:
                confirmed_value = confirmed_entry.get('extracted_value')
                self.logger.info(
                    f"✅ Found CONFIRMED watermark (timestamp: {confirmed_timestamp}): "
                    f"{table_name}.{column_name} = {confirmed_value}"
                )
                return confirmed_value
            else:
                self.logger.info(
                    f"ℹ️ No CONFIRMED watermark found for {table_name}.{column_name}. "
                    f"Will do full incremental (PENDING watermarks are ignored)."
                )
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting watermark: {e}")
            return None
    
    def save_provisional(self, table_name: str, column_name: str, value: str, metadata: Dict[str, Any] = None) -> bool:
        """Guarda watermark PROVISIONAL (PENDING)"""
        try:
            now = datetime.now()
            timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
            
            full_metadata = {
                **(metadata or {}),
                'status': WatermarkStatus.PENDING.value,
                'saved_at': now.isoformat(),
                'transaction_id': f"{table_name}_{column_name}_{now.strftime('%Y%m%d_%H%M%S_%f')}"
            }
            
            success = self.base_storage.set_last_extracted_value(
                table_name=table_name,
                column_name=column_name,
                value=value,
                metadata=full_metadata
            )
            
            if success:
                cache_key = f"{table_name}#{column_name}"
                # 🔑 GUARDAR EL TIMESTAMP PARA USARLO EN CONFIRM
                self._pending_watermarks[cache_key] = {
                    'value': value,
                    'metadata': full_metadata,
                    'saved_at': now,
                    'timestamp': timestamp_str  # ✅ NUEVO: Guardar timestamp exacto
                }
                self.logger.info(f"💾 PENDING watermark saved: {table_name}.{column_name} = {value}")
                return True
            
            return False
                
        except Exception as e:
            self.logger.error(f"Error saving provisional: {e}")
            return False
    
    def confirm(self, table_name: str, column_name: str, additional_metadata: Dict[str, Any] = None) -> bool:
        """
        Confirma watermark PENDING → CONFIRMED (ACTUALIZA el mismo registro)
        Asegura que TODOS los campos estén presentes: WATERMARK_KEY, TIMESTAMP, COLUMN_NAME, 
        EXTRACTED_VALUE, METADATA, PROJECT_NAME, TABLE_NAME, TTL
        """
        try:
            cache_key = f"{table_name}#{column_name}"
            
            if cache_key not in self._pending_watermarks:
                self.logger.warning(f"⚠️ No PENDING watermark to confirm: {table_name}.{column_name}")
                return False
            
            pending = self._pending_watermarks[cache_key]
            watermark_key = self._build_watermark_key(table_name, column_name)
            
            # Metadata actualizada con todos los campos de additional_metadata
            confirmed_metadata = {
                **pending['metadata'],
                'status': WatermarkStatus.CONFIRMED.value,
                'confirmed_at': datetime.now().isoformat(),
                **(additional_metadata or {})
            }
            
            # ✅ SOLUCIÓN: ACTUALIZAR TODOS los campos necesarios del registro PENDING existente
            if hasattr(self.base_storage, 'dynamo_helper'):
                from utils.date_utils import get_current_lima_time
                from datetime import timedelta
                
                # Obtener timestamp actual para TTL
                now = get_current_lima_time()
                ttl_value = int((now + timedelta(days=90)).timestamp())
                
                # Actualizar TODOS los campos necesarios para mantener formato completo
                update_expression = (
                    "SET METADATA = :metadata, "
                    "TABLE_NAME = :table_name, "
                    "COLUMN_NAME = :column_name, "
                    "EXTRACTED_VALUE = :extracted_value, "
                    "PROJECT_NAME = :project_name, "
                    "TTL = :ttl"
                )
                
                expression_attribute_values = {
                    ':metadata': json.dumps(confirmed_metadata),
                    ':table_name': table_name,
                    ':column_name': column_name,
                    ':extracted_value': pending['value'],
                    ':project_name': self.project_name,
                    ':ttl': ttl_value
                }
                
                self.base_storage.dynamo_helper.update_item(
                    partition_key=watermark_key,
                    sort_key=pending['timestamp'],  # ✅ Usar el timestamp guardado
                    update_expression=update_expression,
                    expression_attribute_values=expression_attribute_values
                )
                self.logger.info(
                    f"✅ CONFIRMED watermark (updated in-place): {table_name}.{column_name} "
                    f"- Todos los campos actualizados: WATERMARK_KEY, TIMESTAMP, COLUMN_NAME, "
                    f"EXTRACTED_VALUE, METADATA, PROJECT_NAME, TABLE_NAME, TTL"
                )
            else:
                # Fallback para otros storages que no sean DynamoDB
                success = self.base_storage.set_last_extracted_value(
                    table_name=table_name,
                    column_name=column_name,
                    value=pending['value'],
                    metadata=confirmed_metadata
                )
                if not success:
                    return False
            
            del self._pending_watermarks[cache_key]
            return True
                
        except Exception as e:
            self.logger.error(f"Error confirming: {e}", exc_info=True)
            return False
    
    def rollback(self, table_name: str, column_name: str, error_info: Dict[str, Any] = None) -> bool:
        """Revierte watermark PENDING → ROLLBACK"""
        try:
            cache_key = f"{table_name}#{column_name}"
            
            if cache_key in self._pending_watermarks:
                pending = self._pending_watermarks[cache_key]
                
                rollback_metadata = {
                    **pending['metadata'],
                    'status': WatermarkStatus.ROLLBACK.value,
                    'rollback_at': datetime.now().isoformat(),
                    'error_info': error_info or {}
                }
                
                # Actualizar el registro PENDING a ROLLBACK
                watermark_key = self._build_watermark_key(table_name, column_name)
                
                if hasattr(self.base_storage, 'dynamo_helper'):
                    self.base_storage.dynamo_helper.update_item(
                        partition_key=watermark_key,
                        sort_key=pending['timestamp'],
                        update_expression="SET METADATA = :metadata",
                        expression_attribute_values={
                            ':metadata': json.dumps(rollback_metadata)
                        }
                    )
                else:
                    self.base_storage.set_last_extracted_value(
                        table_name=table_name,
                        column_name=column_name,
                        value=pending['value'],
                        metadata=rollback_metadata
                    )
                
                del self._pending_watermarks[cache_key]
                self.logger.warning(f"🔄 ROLLBACK watermark: {table_name}.{column_name}")
                return True
            
            self.logger.info(f"ℹ️ No PENDING watermark to rollback")
            return True
                
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
    
    def set_last_extracted_value(self, table_name: str, column_name: str, value: str, metadata: Dict[str, Any] = None) -> bool:
        """Método de interfaz - redirige a save_provisional"""
        self.logger.warning("⚠️ Using set_last_extracted_value - consider using save_provisional + confirm")
        return self.save_provisional(table_name, column_name, value, metadata)
    
    def get_extraction_history(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Delega al storage base"""
        return self.base_storage.get_extraction_history(table_name, limit)
    
    def cleanup_old_watermarks(self, days_to_keep: int = 90) -> int:
        """Delega al storage base"""
        return self.base_storage.cleanup_old_watermarks(days_to_keep)
    
    def cleanup_table_watermarks(self, table_name: str) -> Dict[str, Any]:
        """
        Limpia todos los watermarks relacionados con una tabla
        Delega al storage base si tiene este método
        
        Args:
            table_name: Nombre de la tabla (STAGE_TABLE_NAME)
            
        Returns:
            Dict con resultado del cleanup:
            {
                'success': bool,
                'items_deleted': int,
                'details': str,
                'errors': List[str]
            }
        """
        self.logger.info(f"🧹 TransactionalWatermarkStorage: Delegando cleanup a base storage para tabla: {table_name}")
        
        if hasattr(self.base_storage, 'cleanup_table_watermarks'):
            result = self.base_storage.cleanup_table_watermarks(table_name)
            self.logger.info(
                f"✅ Cleanup completado - "
                f"items eliminados: {result.get('items_deleted', 0)}, "
                f"success: {result.get('success', False)}"
            )
            return result
        else:
            self.logger.warning(f"Base storage does not support cleanup_table_watermarks")
            return {
                'success': False,
                'items_deleted': 0,
                'details': 'Base storage does not support cleanup_table_watermarks',
                'errors': ['cleanup_table_watermarks not supported']
            }