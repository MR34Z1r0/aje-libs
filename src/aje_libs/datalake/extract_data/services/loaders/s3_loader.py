# -*- coding: utf-8 -*-
import boto3
import uuid
import time
from decimal import Decimal
from datetime import datetime 
from ...models.file_metadata import FileMetadata
from typing import List, Optional, Dict, Any
import pandas as pd
from ...contracts.loader_interface import ILoader
from aje_libs.datalake.shared.exceptions import StorageException as LoadError
from aje_libs.common.helpers.s3_helper import S3Helper

class S3Loader(ILoader):
    """S3 implementation of LoaderInterface"""
    
    def __init__(self, bucket_name: str, **kwargs):
        self.bucket_name = bucket_name
        self.s3_helper = S3Helper(bucket_name)
        self.region = kwargs.get('region', 'us-east-1')
        self.formatter = None
    
    def set_formatter(self, formatter):
        """Set the file formatter to use"""
        self.formatter = formatter
    
    def load_dataframe(self, df: pd.DataFrame, destination_path: str, 
                      filename: Optional[str] = None, **kwargs) -> tuple:
        """
        Load DataFrame to S3 with metadata capture
        
        Returns:
            Tuple[str, FileMetadata]: (file_path, file_metadata)
        """
        upload_start = time.time()
        
        try:
            if not self.formatter:
                raise LoadError("No formatter set for S3Loader")
            
            # Generate filename if not provided
            if not filename:
                thread_id = kwargs.get('thread_id', 0)
                chunk_id = kwargs.get('chunk_id', 0)
                unique_id = uuid.uuid4().hex[:8]
                base_name = f"data_thread_{thread_id}_chunk_{chunk_id}_{unique_id}"
                filename = base_name + self.formatter.get_file_extension()
            elif not filename.endswith(self.formatter.get_file_extension()):
                filename += self.formatter.get_file_extension()
            
            # Format DataFrame
            extraction_start = time.time()
            file_data = self.formatter.format_dataframe(df, **kwargs)
            extraction_duration = time.time() - extraction_start
            
            # Ensure destination path
            if destination_path.startswith('/'):
                destination_path = destination_path[1:]
            if destination_path and not destination_path.endswith('/'):
                destination_path += '/'
            
            # Build full key
            s3_key = destination_path + filename
            
            # Upload to S3
            upload_file_start = time.time()
            full_s3_path = self.s3_helper.put_object(
                object_key=s3_key,
                body=file_data,
                extra_args={'ContentType': self.formatter.get_content_type()}
            )
            upload_file_duration = time.time() - upload_file_start
            
            # 🆕 Crear metadata del archivo
            file_metadata = FileMetadata(
                file_path=full_s3_path,
                file_name=filename,
                file_size_bytes=len(file_data),
                file_size_mb=FileMetadata.calculate_file_size_mb(len(file_data)),
                records_count=len(df),
                thread_id=str(kwargs.get('thread_id', 0)),
                chunk_id=kwargs.get('chunk_id', 0),
                partition_index=kwargs.get('partition_index'),
                created_at=datetime.now().isoformat(),
                compression=getattr(self.formatter, 'compression', 'none'),
                format=self.formatter.get_file_extension().replace('.', ''),
                extraction_duration_seconds=Decimal(str(round(extraction_duration, 3))),
                upload_duration_seconds=Decimal(str(round(upload_file_duration, 3))),
                columns_count=len(df.columns) if not df.empty else 0,
                estimated_memory_mb=FileMetadata.estimate_memory_mb(df.shape)
            )
            
            return file_metadata.to_dict()
            
        except Exception as e:
            raise LoadError(f"Failed to load DataFrame to S3: {e}")
    
    def delete_existing(self, path: str) -> bool:
        """Delete existing data at S3 path"""
        try:
            # Remove s3:// prefix if present
            if path.startswith('s3://'):
                path = path[5:]
            
            # Remove bucket name if present in path
            if path.startswith(f"{self.bucket_name}/"):
                path = path[len(self.bucket_name) + 1:]
            
            # List objects with prefix
            objects = self.s3_helper.list_objects(prefix=path)
            
            if objects:
                keys_to_delete = [obj['Key'] for obj in objects]
                result = self.s3_helper.delete_objects(keys_to_delete)
                return True
            
            return True  # No objects to delete is considered success
            
        except Exception as e:
            raise LoadError(f"Failed to delete existing data at {path}: {e}")
    
    def cleanup_table_data(self, table_path: str) -> Dict[str, Any]:
        """
        Limpia todos los objetos relacionados con una tabla en S3 Raw bucket
        
        Args:
            table_path: Ruta completa de la tabla (ej: team/datasource/endpoint/table_name/)
            
        Returns:
            Dict con resultado del cleanup:
            {
                'success': bool,
                'items_deleted': int,
                'details': str,
                'errors': List[str]
            }
        """
        from ....shared.services.logging import LoggerService
        logger = LoggerService.get_logger(__name__)
        
        result = {
            'success': False,
            'items_deleted': 0,
            'details': '',
            'errors': []
        }
        
        try:
            # Normalizar path
            if table_path.startswith('s3://'):
                table_path = table_path[5:]
            
            if table_path.startswith(f"{self.bucket_name}/"):
                table_path = table_path[len(self.bucket_name) + 1:]
            
            # Asegurar que termine con /
            if not table_path.endswith('/'):
                table_path += '/'
            
            logger.debug(f"Limpiando S3 - bucket: {self.bucket_name}, path: {table_path}")
            
            # Listar todos los objetos con este prefijo
            objects = self.s3_helper.list_objects(prefix=table_path)
            
            if not objects:
                logger.debug(f"No se encontraron objetos para limpiar en {table_path}")
                result['success'] = True
                result['details'] = f"No se encontraron objetos en {table_path}"
                return result
            
            # Extraer keys de los objetos
            keys_to_delete = [obj['Key'] for obj in objects]
            total_objects = len(keys_to_delete)
            
            # Eliminar objetos en lotes (S3 permite hasta 1000 por batch)
            batch_size = 1000
            deleted_count = 0
            batch_errors = []
            
            for i in range(0, len(keys_to_delete), batch_size):
                batch = keys_to_delete[i:i + batch_size]
                
                try:
                    delete_result = self.s3_helper.delete_objects(batch)
                    deleted_in_batch = len(delete_result.get('Deleted', []))
                    deleted_count += deleted_in_batch
                    
                    # Solo loguear cada 10 batches o si hay error
                    batch_num = i//batch_size + 1
                    if batch_num % 10 == 0 or batch_num == 1:
                        logger.debug(f"Batch {batch_num}: {deleted_in_batch} objetos eliminados")
                    
                    # Si hay errores en el batch
                    if 'Errors' in delete_result and delete_result['Errors']:
                        errors = [err.get('Message', 'Unknown error') for err in delete_result['Errors']]
                        result['errors'].extend(errors)
                        batch_errors.extend(errors)
                        
                except Exception as e:
                    error_msg = f"Error eliminando batch {i//batch_size + 1}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
            
            result['success'] = deleted_count > 0 or total_objects == 0
            result['items_deleted'] = deleted_count
            result['details'] = f"Eliminados {deleted_count} de {total_objects} objetos"
            
            # Agrupar resultado final
            if batch_errors:
                logger.warning(f"⚠️ Limpieza S3 completada con errores - Eliminados: {deleted_count}/{total_objects}, Errores: {len(batch_errors)}")
            elif deleted_count > 0:
                logger.info(f"✅ Limpieza S3 completada - {deleted_count}/{total_objects} objetos eliminados")
            
            return result
            
        except Exception as e:
            error_msg = f"Error durante limpieza S3: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)
            result['details'] = error_msg
            return result
    
    def list_files(self, path: str) -> List[str]:
        """List files at S3 path"""
        try:
            # Remove s3:// prefix if present
            if path.startswith('s3://'):
                path = path[5:]
            
            # Remove bucket name if present in path
            if path.startswith(f"{self.bucket_name}/"):
                path = path[len(self.bucket_name) + 1:]
            
            objects = self.s3_helper.list_objects(prefix=path)
            return [f"s3://{self.bucket_name}/{obj['Key']}" for obj in objects]
            
        except Exception as e:
            raise LoadError(f"Failed to list files at {path}: {e}")
    
    def path_exists(self, path: str) -> bool:
        """Check if S3 path exists"""
        try:
            # Remove s3:// prefix if present
            if path.startswith('s3://'):
                path = path[5:]
            
            # Remove bucket name if present in path
            if path.startswith(f"{self.bucket_name}/"):
                path = path[len(self.bucket_name) + 1:]
            
            # Check if it's a specific object or prefix
            if path.endswith('/'):
                # It's a prefix, check if any objects exist with this prefix
                objects = self.s3_helper.list_objects(prefix=path, max_keys=1)
                return len(objects) > 0
            else:
                # It's a specific object
                return self.s3_helper.object_exists(path)
                
        except Exception:
            return False