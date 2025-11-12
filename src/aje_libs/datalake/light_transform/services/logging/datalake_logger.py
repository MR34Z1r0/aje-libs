"""
Servicios de logging específicos para light_transform.

Incluye:
- DataLakeLogger: wrapper para configurar loggers homogéneos
- DynamoDBLogger: almacenamiento de logs de proceso en DynamoDB + SNS
- Monitor: fachada para registrar eventos únicos (start/success/error/warning)
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
import pytz
from boto3.dynamodb.conditions import Key

from aje_libs.datalake.shared.contracts.logging import ILogger
from aje_libs.datalake.shared.factories.logger_factory import LoggerFactory
from aje_libs.datalake.shared.services.logging.logger_service import LoggerService


TZ_LIMA = pytz.timezone('America/Lima')


class DataLakeLogger:
    """
    Clase centralizada para logging en DataLake que maneja automáticamente:
    - AWS CloudWatch (en entorno Glue)
    - Console output
    - Detección automática del entorno (AWS vs Local)
    """

    # Configuración global por defecto
    _global_config = {
        'log_level': logging.INFO,
        'service_name': 'light_transform',
        'correlation_id': None,
        'owner': None,
        'auto_detect_env': True,
        'force_local_mode': False,
        'log_directory': './logs'
    }

    # Cache de loggers para evitar recrear
    _logger_cache: Dict[str, logging.Logger] = {}

    @classmethod
    def configure_global(
        cls,
        log_level: Optional[int] = None,
        service_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        owner: Optional[str] = None,
        auto_detect_env: bool = True,
        force_local_mode: bool = False,
        log_directory: Optional[str] = None
    ):
        """Configura parámetros globales para todos los loggers"""
        if log_level is not None:
            cls._global_config['log_level'] = log_level
        if service_name is not None:
            cls._global_config['service_name'] = service_name
        if correlation_id is not None:
            cls._global_config['correlation_id'] = correlation_id
        if owner is not None:
            cls._global_config['owner'] = owner
        if log_directory is not None:
            cls._global_config['log_directory'] = log_directory

        cls._global_config['auto_detect_env'] = auto_detect_env
        cls._global_config['force_local_mode'] = force_local_mode

        # Aplicar configuración global a LoggerService y limpiar cache
        LoggerService.configure_global(
            log_level=cls._global_config['log_level'],
            log_directory=cls._global_config['log_directory'],
            service_name=cls._global_config['service_name'],
            correlation_id=cls._global_config['correlation_id'],
            owner=cls._global_config['owner'],
            auto_detect_env=cls._global_config['auto_detect_env'],
            force_local_mode=cls._global_config['force_local_mode']
        )

        cls._logger_cache.clear()

    @classmethod
    def get_logger(
        cls,
        name: Optional[str] = None,
        service_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        log_level: Optional[int] = None
    ) -> logging.Logger:
        """Obtiene un logger configurado para el entorno actual"""

        effective_service = service_name or cls._global_config['service_name']
        effective_correlation_id = correlation_id or cls._global_config['correlation_id']
        effective_log_level = log_level or cls._global_config['log_level']

        # Crear cache key
        cache_key = f"{name}_{effective_service}_{effective_correlation_id}_{effective_log_level}"

        # Devolver del cache si existe
        if cache_key in cls._logger_cache:
            return cls._logger_cache[cache_key]

        # Ajustar configuración global temporalmente
        LoggerService.configure_global(
            log_level=effective_log_level,
            service_name=effective_service,
            correlation_id=effective_correlation_id,
            owner=cls._global_config['owner'],
            auto_detect_env=cls._global_config['auto_detect_env'],
            force_local_mode=cls._global_config['force_local_mode'],
            log_directory=cls._global_config['log_directory']
        )

        # Crear logger usando la fábrica compartida
        logger_service: ILogger = LoggerFactory.create(
            logger_type='datalake',
            logger_name=name or effective_service or 'light_transform'
        )
        logger = logger_service._logger if hasattr(logger_service, '_logger') else LoggerService.get_logger(name)

        cls._logger_cache[cache_key] = logger
        return logger


class DynamoDBLogger:
    """
    Logger para DynamoDB que registra logs de proceso y envía notificaciones SNS en caso de errores
    """

    def __init__(
        self,
        table_name: str,
        sns_topic_arn: Optional[str] = None,
        team: str = "",
        data_source: str = "",
        endpoint_name: str = "",
        flow_name: str = "",
        environment: str = "",
        region: str = "us-east-1",
        logger_name: Optional[str] = None,
        process_guid: Optional[str] = None
    ):
        """Inicializa el DynamoDB Logger"""
        self.table_name = table_name
        self.sns_topic_arn = sns_topic_arn
        self.team = team
        self.data_source = data_source
        self.endpoint_name = endpoint_name
        self.flow_name = flow_name
        self.environment = environment
        self.process_guid = process_guid or str(uuid.uuid4())

        # Configurar timezone Lima
        self.tz_lima = pytz.timezone('America/Lima')

        # Obtener logger usando DataLakeLogger
        self.logger = DataLakeLogger.get_logger(
            name=logger_name or f"{team}-{data_source}-dynamodb-logger",
            service_name=f"{team}-{flow_name}" if team and flow_name else None,
            correlation_id=f"{team}-{data_source}-{flow_name}" if team and data_source and flow_name else None
        )

        # Clientes AWS
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.dynamodb_table = self.dynamodb.Table(table_name) if table_name else None
            self.sns_client = boto3.client('sns', region_name=region) if sns_topic_arn else None

            self.logger.info(f"DynamoDBLogger inicializado - Tabla: {table_name}, SNS: {bool(sns_topic_arn)}")

        except Exception as e:
            self.logger.warning(f"Error inicializando clientes AWS: {e}")
            self.dynamodb_table = None
            self.sns_client = None

    def log_process_status(
        self,
        status: str,  # RUNNING, SUCCESS, FAILED, WARNING
        message: str,
        table_name: str = "",
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra el estatus de un proceso en DynamoDB"""
        if not self.dynamodb_table:
            self.logger.warning(f"DynamoDB no configurado, log no registrado: {status} - {message}")
            return ""

        try:
            # Generar timestamp y process_id únicos
            now_lima = dt.datetime.now(pytz.utc).astimezone(self.tz_lima)
            timestamp = now_lima.strftime("%Y%m%d_%H%M%S_%f")
            process_id = f"{self.team}-{self.data_source}-{self.endpoint_name}-{table_name}".lower()

            # Preparar contexto con límites de tamaño
            log_context = self._prepare_context(context or {})

            # Truncar mensaje si es muy largo
            truncated_message = message if len(message) <= 2000 else message[:2000] + "...[TRUNCATED]"

            # Crear registro compatible con estructura existente
            record = {
                "PROCESS_ID": process_id,
                "PROCESS_GUID": self.process_guid,
                "DATE_SYSTEM": timestamp,
                "RESOURCE_NAME": job_name or "unknown_job",
                "RESOURCE_TYPE": "python_shell_glue_job",
                "STATUS": status.upper(),
                "MESSAGE": truncated_message,
                "PROCESS_TYPE": self._get_process_type(status),
                "CONTEXT": log_context,
                "TEAM": self.team,
                "DATASOURCE": self.data_source,
                "ENDPOINT_NAME": self.endpoint_name,
                "TABLE_NAME": table_name,
                "ENVIRONMENT": self.environment,
                "LOG_CREATED_AT": now_lima.strftime("%Y-%m-%d %H:%M:%S")
            }

            # Insertar en DynamoDB
            self.dynamodb_table.put_item(Item=record)
            self.logger.info(f"Log registrado en DynamoDB - process_id={process_id}, status={status}, table={table_name}")

            # Enviar notificación SNS si es error
            if status.upper() == "FAILED":
                self._send_failure_notification(record)

            return process_id

        except Exception as e:
            self.logger.error(f"Error registrando log en DynamoDB: {e}")

            # Si falló el registro pero era un error, intentar enviar SNS de emergencia
            if status.upper() == "FAILED":
                self._send_emergency_notification(message, table_name, str(e))

            return ""

    def log_start(
        self,
        table_name: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra inicio de proceso"""
        message = f"Iniciando procesamiento de tabla {table_name} job {job_name}"
        self.logger.info(message)
        return self.log_process_status("RUNNING", message, table_name, job_name, context)

    def log_success(
        self,
        table_name: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra éxito de proceso"""
        message = f"Procesamiento exitoso de tabla {table_name} job {job_name}"
        self.logger.info(message)
        return self.log_process_status("SUCCESS", message, table_name, job_name, context)

    def log_failure(
        self,
        table_name: str,
        error_message: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra fallo de proceso y envía notificación"""
        message = f"Error procesando tabla {table_name} job {job_name} error: {error_message}"
        self.logger.error(message)
        return self.log_process_status("FAILED", message, table_name, job_name, context)

    def log_warning(
        self,
        table_name: str,
        warning_message: str,
        job_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra advertencia de proceso"""
        message = f"Advertencia procesando tabla {table_name} job {job_name} warning: {warning_message}"
        self.logger.warning(message)
        return self.log_process_status("WARNING", message, table_name, job_name, context)

    def delete_logs(self, table_name: str, process_id: Optional[str] = None) -> int:
        """Elimina todos los logs asociados a un PROCESS_ID."""
        if not self.dynamodb_table:
            self.logger.warning("DynamoDB no configurado, no se pueden eliminar logs")
            return 0

        effective_process_id = (process_id or f"{self.team}-{self.data_source}-{self.endpoint_name}-{table_name}").lower()
        self.logger.info(
            f"🧹 Eliminando logs del process_id '{effective_process_id}' en tabla DynamoDB {self.table_name}"
        )

        deleted = 0
        query_kwargs = {
            'KeyConditionExpression': Key('PROCESS_ID').eq(effective_process_id)
        }

        try:
            while True:
                response = self.dynamodb_table.query(**query_kwargs)
                items = response.get('Items', [])

                if not items:
                    break

                for item in items:
                    date_system = item.get('DATE_SYSTEM')
                    if not date_system:
                        continue
                    self.dynamodb_table.delete_item(
                        Key={
                            'PROCESS_ID': effective_process_id,
                            'DATE_SYSTEM': date_system
                        }
                    )
                    deleted += 1

                last_evaluated = response.get('LastEvaluatedKey')
                if not last_evaluated:
                    break
                query_kwargs['ExclusiveStartKey'] = last_evaluated

            self.logger.info(
                f"✅ Logs eliminados: {deleted} registros para process_id '{effective_process_id}'"
            )
            return deleted
        except Exception as exc:
            self.logger.error(f"Error eliminando logs en DynamoDB: {exc}", exc_info=True)
            return deleted

    def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara el contexto limitando su tamaño para DynamoDB"""
        MAX_CONTEXT_SIZE = 300 * 1024  # 300KB

        def truncate_data(data, max_length=1000):
            """Trunca estructuras de datos"""
            if isinstance(data, str):
                return data if len(data) <= max_length else data[:max_length] + "...[TRUNCATED]"
            if isinstance(data, dict):
                truncated = {}
                for idx, (k, v) in enumerate(data.items()):
                    if idx >= 10:
                        truncated["_truncated_items"] = f"...and {len(data) - 10} more items"
                        break
                    truncated[k] = truncate_data(v, 500)
                return truncated
            if isinstance(data, list):
                truncated = [truncate_data(item, 200) for item in data[:5]]
                if len(data) > 5:
                    truncated.append(f"...and {len(data) - 5} more items")
                return truncated
            return str(data)[:500] if data is not None else data

        prepared_context = truncate_data(context)

        # Verificar tamaño total
        context_json = json.dumps(prepared_context, default=str)
        if len(context_json.encode("utf-8")) > MAX_CONTEXT_SIZE:
            return {
                "size_limit_applied": "Context truncated due to DynamoDB size limits",
                "original_keys": list(context.keys())[:10],
                "truncated_at": dt.datetime.now(self.tz_lima).strftime("%Y-%m-%d %H:%M:%S")
            }

        return prepared_context

    def _get_process_type(self, status: str) -> str:
        """Determina el tipo de proceso basado en el status"""
        status_upper = status.upper()
        if status_upper == "RUNNING":
            return "incremental"
        if status_upper == "SUCCESS":
            return "completed"
        if status_upper == "WARNING":
            return "incremental_with_warnings"
        return "error_handling"

    def _send_failure_notification(self, record: Dict[str, Any]):
        """Envía notificación SNS por error"""
        if not self.sns_client or not self.sns_topic_arn:
            self.logger.warning("SNS no configurado, no se puede enviar notificación de error")
            return

        try:
            message_text = str(record.get("MESSAGE", ""))
            truncated_message = message_text[:800] + "..." if len(message_text) > 800 else message_text

            notification_message = f"""
🚨 PROCESO FALLIDO EN LIGHT TRANSFORM

📊 DETALLES:
- Estado: {record.get('STATUS')}
- Tabla: {record.get("TABLE_NAME")}
- Equipo: {record.get("TEAM")}
- Flujo: {self.flow_name}
- Ambiente: {record.get("ENVIRONMENT")}
- Timestamp: {record.get("LOG_CREATED_AT")}

❌ ERROR:
{truncated_message}

🔍 IDENTIFICADORES:
- Process ID: {record.get('PROCESS_ID')}
- Resource: {record.get('RESOURCE_NAME')}

📋 ACCIONES:
1. Consulta logs completos en DynamoDB usando el PROCESS_ID
2. Revisa CloudWatch logs para más detalles
3. Verifica la configuración de la tabla y transformaciones

⚠️ Este mensaje se envía automáticamente. El job se marca como SUCCESS para evitar dobles notificaciones.
            """

            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=f"🚨 [ERROR] LIGHT TRANSFORM - {record.get('TABLE_NAME')} - {record.get('TEAM')}",
                Message=notification_message
            )

            self.logger.info("Notificación SNS enviada exitosamente")

        except Exception as e:
            self.logger.error(f"Error enviando notificación SNS: {e}")

    def _send_emergency_notification(self, message: str, table_name: str, dynamodb_error: str):
        """Envía notificación de emergencia cuando falla DynamoDB"""
        if not self.sns_client or not self.sns_topic_arn:
            return

        try:
            emergency_message = f"""
🆘 NOTIFICACIÓN DE EMERGENCIA - FALLO EN SISTEMA DE LOGGING

⚠️ SITUACIÓN CRÍTICA:
El proceso falló Y el sistema de logging a DynamoDB también falló.

📊 DETALLES DEL ERROR ORIGINAL:
- Tabla: {table_name}
- Equipo: {self.team}
- Flujo: {self.flow_name}
- Error: {message[:500]}

🔧 ERROR DE DYNAMODB:
{dynamodb_error[:300]}

🚨 ACCIÓN REQUERIDA:
1. Revisar logs de CloudWatch INMEDIATAMENTE
2. Verificar conectividad a DynamoDB
3. Revisar permisos IAM
4. Investigar el error original del proceso

⚠️ Sin logging en DynamoDB, la trazabilidad está comprometida.
            """

            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=f"🆘 [EMERGENCIA] Sistema de Logging Fallido - {table_name}",
                Message=emergency_message
            )

            self.logger.critical("Notificación de emergencia enviada")

        except Exception as e:
            self.logger.critical(f"Error crítico: No se pudo enviar notificación de emergencia: {e}")


class Monitor:
    """
    Monitor para Light Transform siguiendo el patrón de extract_data_v2
    Centraliza todas las llamadas de logging a DynamoDB para evitar duplicados
    """

    def __init__(self, dynamo_logger: DynamoDBLogger):
        """
        Inicializa el monitor con un DynamoDBLogger

        Args:
            dynamo_logger: Instancia de DynamoDBLogger para registrar eventos
        """
        self.dynamo_logger = dynamo_logger
        self.process_id: Optional[str] = None

    def log_start(self, table_name: str, job_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Registra el inicio de la transformación - ÚNICA LLAMADA
        """
        self.process_id = self.dynamo_logger.log_start(
            table_name=table_name,
            job_name=job_name,
            context=context or {}
        )
        return self.process_id

    def log_success(self, table_name: str, job_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Registra el éxito de la transformación - ÚNICA LLAMADA
        """
        return self.dynamo_logger.log_success(
            table_name=table_name,
            job_name=job_name,
            context=context or {}
        )

    def log_error(self, table_name: str, error_message: str, job_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Registra un error en la transformación - ÚNICA LLAMADA
        """
        return self.dynamo_logger.log_failure(
            table_name=table_name,
            error_message=error_message,
            job_name=job_name,
            context=context or {}
        )

    def log_warning(self, table_name: str, warning_message: str, job_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Registra una advertencia en la transformación
        """
        return self.dynamo_logger.log_warning(
            table_name=table_name,
            warning_message=warning_message,
            job_name=job_name,
            context=context or {}
        )

    def get_process_id(self) -> Optional[str]:
        """Retorna el process_id actual"""
        return self.process_id

    def cleanup_logs(self, table_name: str, process_id: Optional[str] = None) -> int:
        """Elimina los logs asociados a la ejecución actual."""
        return self.dynamo_logger.delete_logs(table_name=table_name, process_id=process_id)


__all__ = [
    "DataLakeLogger",
    "DynamoDBLogger",
    "Monitor",
]

