"""
Implementación específica de EventLoggerService para extract_data usando DynamoDBLogStorage
"""
import os
import pytz
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from ....shared.contracts.monitoring import IEventLogger
from ....shared.contracts.logging import ILogger
from ..log_storage.dynamodb_log_storage import DynamoDBLogStorage


def sanitize_for_dynamodb(obj):
    """
    Sanitiza objetos para DynamoDB convirtiendo tipos no soportados.
    
    - float -> Decimal
    - inf/nan -> None
    - Recursivo para dict y list
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_dynamodb(item) for item in obj]
    elif isinstance(obj, float):
        # Manejar casos especiales
        if obj != obj or obj == float('inf') or obj == float('-inf'):
            return None
        return Decimal(str(obj))
    elif isinstance(obj, set):
        return {sanitize_for_dynamodb(item) for item in obj if item is not None}
    return obj


class ExtractDataEventLoggerService(IEventLogger):
    """
    Implementación específica de EventLoggerService para extract_data
    Usa DynamoDBLogStorage para almacenar logs en DynamoDB
    """
    
    def __init__(
        self,
        log_storage: DynamoDBLogStorage,
        team: str = "",
        data_source: str = "",
        endpoint_name: str = "",
        flow_name: str = "extract_data",
        environment: str = "",
        logger: Optional[ILogger] = None,
        process_guid: Optional[str] = None
    ):
        """
        Inicializa el servicio de registro de eventos
        
        Args:
            log_storage: Instancia de DynamoDBLogStorage
            team: Nombre del equipo
            data_source: Fuente de datos
            endpoint_name: Nombre del endpoint
            flow_name: Nombre del flujo (extract_data, light_transform)
            environment: Ambiente (DEV, PROD, etc.)
            logger: Logger para logs internos (DIP, opcional)
            process_guid: GUID del proceso (opcional)
        """
        self.log_storage = log_storage
        self.team = team
        self.data_source = data_source
        self.endpoint_name = endpoint_name
        self.flow_name = flow_name
        self.environment = environment
        self.process_guid = process_guid or str(uuid.uuid4())
        self.tz_lima = pytz.timezone('America/Lima')
        self.logger = logger
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Registra un evento"""
        try:
            log_entry = {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": event_data.get("timestamp")
            }
            return self.log_storage.put_log(log_entry)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error registrando evento: {e}")
            return False
    
    def log_process_status(
        self,
        status: str,
        message: str,
        table_name: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra estado de proceso en DynamoDB
        
        Args:
            status: Estado del proceso (RUNNING, SUCCESS, FAILED, WARNING)
            message: Mensaje descriptivo
            table_name: Nombre de la tabla que se está procesando
            job_name: Nombre del job
            context: Contexto adicional
            
        Returns:
            process_id: ID único del proceso registrado
        """
        if not self.log_storage:
            if self.logger:
                self.logger.warning(f"DynamoDB no configurado, log no registrado: {status} - {message}")
            return ""
        
        try:
            # Generar timestamp y process_id únicos
            now_lima = datetime.now(pytz.utc).astimezone(self.tz_lima)
            timestamp = now_lima.strftime("%Y%m%d_%H%M%S_%f")
            process_id = f"{self.team}-{self.data_source}-{self.endpoint_name}-{table_name}".lower()
            
            # Preparar contexto con límites de tamaño
            log_context = self._prepare_enhanced_context(context or {}, status, table_name)
            
            # Detectar runtime (local, glue, databricks)
            runtime_type = self._detect_runtime()
            
            # Obtener type_load (strategy) del contexto, si no está usar "unknown"
            type_load = context.get('strategy', 'unknown') if context else 'unknown'
            
            # Obtener load_mode del contexto, si no está usar "unknown"
            load_mode = context.get('load_mode', 'unknown') if context else 'unknown'
            
            # Crear registro compatible con la estructura existente
            record = {
                "PROCESS_ID": process_id,
                "PROCESS_GUID": self.process_guid,
                "DATE_SYSTEM": timestamp,
                "RESOURCE_NAME": "extract_data",  # Siempre "extract_data"
                "RESOURCE_TYPE": runtime_type,  # local, glue, o databricks
                "STATUS": status.upper(),
                "MESSAGE": message,
                "TYPE_LOAD": type_load,  # Strategy de tables.csv (full, incremental, time_range)
                "LOAD_MODE": load_mode,  # Modo de carga (normal, initial, reset, reprocess)
                "CONTEXT": log_context,
                "TEAM": self.team,
                "DATASOURCE": self.data_source,
                "ENDPOINT_NAME": self.endpoint_name,
                "TABLE_NAME": table_name,
                "ENVIRONMENT": self.environment,
                "LOG_CREATED_AT": now_lima.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Insertar en DynamoDB usando el storage
            success = self.log_storage.put_log(record)
            
            if success:
                if self.logger:
                    self.logger.info(f"Log registrado en DynamoDB", {
                        "process_id": process_id, 
                        "process_guid": self.process_guid,
                        "status": status,
                        "table": table_name
                    })
                
                return process_id
            else:
                raise Exception("Failed to put log via storage")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error registrando log en DynamoDB: {e}")
            return ""
    
    def _prepare_enhanced_context(self, context: Dict[str, Any], status: str, table_name: str) -> Dict[str, Any]:
        """
        Prepara el contexto con datos adicionales específicos por estado
        """
        # Preparar contexto base con límites de tamaño
        enhanced_context = self._prepare_context(context)
        
        # Agregar metadata común para todos los estados
        enhanced_context.update({
            "status_type": status.upper(),
            "execution_timestamp": datetime.now(self.tz_lima).isoformat(),
            "pipeline_component": self.flow_name,
            "source_system": self.data_source
        })
        
        # NO incluir load_mode ni strategy en el contexto ya que están como campos directos
        # (TYPE_LOAD y LOAD_MODE) en el registro de DynamoDB
        
        # Datos específicos por estado
        if status.upper() == "RUNNING":
            enhanced_context.update({
                "start_time": context.get("start_time", datetime.now(self.tz_lima).isoformat()),
                "expected_duration_minutes": context.get("expected_duration_minutes"),
                "batch_size": context.get("batch_size"),
                "parallel_workers": context.get("parallel_workers")
            })
        
        elif status.upper() == "SUCCESS":
            success_data = {
                "end_time": context.get("end_time", datetime.now(self.tz_lima).isoformat()),
                "success_rate": context.get("success_rate", "100%")
            }
            if context.get("duration_seconds"):
                success_data["duration_seconds"] = context.get("duration_seconds")
            if context.get("records_processed"):
                success_data["records_processed"] = context.get("records_processed")
            if context.get("data_size_mb"):
                success_data["data_size_mb"] = context.get("data_size_mb")
            
            enhanced_context.update(success_data)
        
        elif status.upper() == "FAILED":
            enhanced_context.update({
                "error_time": context.get("error_time", datetime.now(self.tz_lima).isoformat()),
                "error_type": context.get("error_type", "UnknownError"),
                "error_details": context.get("error_details", ""),
                "failed_at_step": context.get("failed_at_step"),
                "records_processed_before_failure": context.get("records_processed", 0),
                "retry_count": context.get("retry_count", 0),
                "is_retryable": context.get("is_retryable", False),
                "stack_trace": context.get("stack_trace", "")[:1000]
            })
        
        elif status.upper() == "WARNING":
            enhanced_context.update({
                "warning_time": context.get("warning_time", datetime.now(self.tz_lima).isoformat()),
                "warning_type": context.get("warning_type", "GeneralWarning"),
                "warning_details": context.get("warning_details", ""),
                "affected_records": context.get("affected_records", 0),
                "records_with_issues": context.get("records_with_issues", 0),
                "data_quality_score": context.get("data_quality_score"),
                "can_continue": context.get("can_continue", True),
                "remediation_applied": context.get("remediation_applied", False)
            })
        
        return enhanced_context
    
    def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara el contexto limitando su tamaño para DynamoDB"""
        MAX_CONTEXT_SIZE = 300 * 1024  # 300KB
        
        sanitized_context = sanitize_for_dynamodb(context)
        prepared_context = sanitized_context
        
        # Verificar tamaño total
        import json
        context_json = json.dumps(prepared_context, default=str)
        if len(context_json.encode("utf-8")) > MAX_CONTEXT_SIZE:
            return {
                "size_limit_applied": "Context truncated due to DynamoDB size limits",
                "original_keys": list(context.keys())[:10],
                "truncated_at": datetime.now(self.tz_lima).strftime("%Y-%m-%d %H:%M:%S")
            }
        
        return prepared_context
    
    def _detect_runtime(self) -> str:
        """
        Detecta el runtime donde se está ejecutando el código.
        
        Returns:
            "local", "glue", o "databricks"
        """
        # Detectar AWS Glue - usar variables de entorno específicas de Glue
        # AWS Glue establece estas variables cuando se ejecuta en un job
        if os.getenv("AWS_GLUE_JOB_NAME") or os.getenv("AWS_GLUE_JOB_RUN_ID"):
            return "glue"
        
        # Detectar Databricks - usar variable de entorno específica
        if os.getenv("DATABRICKS_RUNTIME_VERSION"):
            return "databricks"
        
        # Verificar si estamos en un entorno Lambda/Glue por el path de ejecución
        # (solo como fallback, ya que AWS_EXECUTION_ENV puede estar en local)
        if os.getenv("AWS_EXECUTION_ENV") and os.path.exists("/opt/python"):
            return "glue"
        
        # Por defecto, asumir local
        return "local"

