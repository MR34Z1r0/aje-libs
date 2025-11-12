"""
Orquestador principal para ejecutar light_transform utilizando aje_libs y factories.
"""
from __future__ import annotations

import datetime as dt
import logging
import sys
import uuid
from typing import Any, Optional

import boto3
import pytz
from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession

from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConfigurationError,
    DataValidationError as DataValidationException,
    MonitoringError,
    ProcessingError,
    TransformationException,
    TransformationWarningException,
    WatermarkError,
)
from aje_libs.datalake.light_transform.factories import (
    LightTransformConfigFactory,
    LightTransformProcessorFactory,
)
from aje_libs.datalake.light_transform.models import LightTransformConfig
from aje_libs.datalake.light_transform.services import DataLakeLogger
from aje_libs.datalake.shared.factories import MonitorFactory
from aje_libs.datalake.shared.contracts.monitoring import IMonitor
from aje_libs.datalake.shared.services.logging import LoggerService

TZ_LIMA = pytz.timezone('America/Lima')


class LightTransformOrchestrator:
    """Coordina la ejecución de Light Transform aplicando principios SOLID."""

    REQUIRED_ARGS = [
        'job_name',
        'raw_bucket',
        'stage_bucket',
        'logs_table',
        'table_name',
        'topic_arn',
        'project_name',
        'team',
        'data_source',
        'tables',
        'credentials',
        'columns',
        'endpoint_name',
        'environment',
        'date_process',
        'load_mode',
        'watermarks_table'
    ]

    def __init__(self):
        self.logger = None
        self.monitor: Optional[IMonitor] = None
        self.spark: Optional[SparkSession] = None
        self.s3_client = None
        self.process_guid = str(uuid.uuid4())
        self.start_time = dt.datetime.now()
        self.process_id: Optional[str] = None
        self.last_status: str = "idle"
        self.last_error_type: Optional[str] = None
        self.last_error_message: Optional[str] = None

    def parse_arguments(self, argv: Any) -> dict:
        args = getResolvedOptions(argv, self.REQUIRED_ARGS)
        if '--LOG_LEVEL' in argv:
            optional = getResolvedOptions(argv, ['LOG_LEVEL'])
            args['LOG_LEVEL'] = optional.get('LOG_LEVEL', 'INFO')
        else:
            args['LOG_LEVEL'] = 'INFO'
        # Mantener compatibilidad con NONE
        if args.get('DATE_PROCESS', '').upper() == "NONE":
            args['DATE_PROCESS'] = None
        return args

    def initialize_logging(self, config: LightTransformConfig, log_level: str = 'INFO') -> None:
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }

        LoggerService.configure_global(
            log_level=log_level_map.get(log_level.upper(), logging.INFO),
            service_name="light_transform",
            correlation_id=f"{config.team}-{config.data_source}-light_transform-{config.table_name}",
            owner=config.team,
            auto_detect_env=True,
            force_local_mode=False
        )

        DataLakeLogger.configure_global(
            log_level=log_level_map.get(log_level.upper(), logging.INFO),
            service_name="light_transform",
            correlation_id=f"{config.team}-{config.data_source}-light_transform-{config.table_name}",
            owner=config.team,
            auto_detect_env=True,
            force_local_mode=False
        )

        self.logger = LoggerService.get_logger(__name__)
        LoggerService.print_environment_info()
        self.logger.info(f"🆔 Process GUID generado: {self.process_guid}")

    def initialize_monitoring(self, config: LightTransformConfig) -> None:
        log_storage = config.log_storage
        notification = config.notification_target
        table_name = None
        if log_storage and log_storage.provider == 'dynamodb':
            table_name = log_storage.location
        sns_topic = None
        if notification and notification.provider == 'sns':
            sns_topic = notification.location

        self.monitor = MonitorFactory.create(
            monitor_type=config.monitor_type,
            logger=self.logger,
            table_name=table_name,
            project_name=config.project_name,
            team=config.team,
            data_source=config.data_source,
            endpoint_name=config.endpoint_name,
            environment=config.environment,
            sns_topic_arn=sns_topic,
            process_guid=self.process_guid,
            flow_name='light_transform'
        )

    def log_start(self, config: LightTransformConfig) -> None:
        tables_source = config.config_sources.get('tables')
        source_desc = (
            f"{config.source_storage.provider}:{config.source_storage.location}"
            if config.source_storage
            else "N/A"
        )
        stage_desc = (
            f"{config.stage_storage.provider}:{config.stage_storage.location}"
            if config.stage_storage
            else "N/A"
        )
        tables_location = (
            f"{tables_source.provider}:{tables_source.location}" if tables_source else "N/A"
        )

        context = {
            "start_time": self.start_time.isoformat(),
            "process_guid": self.process_guid,
            "source_storage": source_desc,
            "stage_storage": stage_desc,
            "tables_config": tables_location,
            "flow_type": "light_transform",
            "date_process": config.date_process or dt.datetime.now(TZ_LIMA).strftime('%Y-%m-%d'),
            "is_reprocessing": bool(config.date_process)
        }

        if self.monitor:
            self.process_id = self.monitor.log_start(
                table_name=config.table_name,
                job_name=config.job_name,
                metadata=context
            )

        self.logger.info(
            f"🚀 Iniciando Light Transform table: {config.table_name} job: {config.job_name} "
            f"team: {config.team} data_source: {config.data_source} "
            f"endpoint: {config.endpoint_name} process_id: {self.process_id}"
        )

    def initialize_spark(self) -> None:
        self.spark = SparkSession.builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
            .config("spark.databricks.delta.schema.autoMerge.enabled", "true") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.adaptive.skewJoin.enabled", "true") \
            .config("spark.sql.adaptive.localShuffleReader.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
            .getOrCreate()

        self.spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        self.spark.sparkContext._jsc.hadoopConfiguration().set("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")

    def build_processor(self, config: LightTransformConfig) -> LightTransformProcessorFactory:
        return LightTransformProcessorFactory(
            spark=self.spark,
            s3_client=self.s3_client,
            logger=self.logger,
            config_source_type=config.config_source_type,
            data_loader_type=config.data_loader_type,
            data_writer_type=config.data_writer_type,
        )

    def finalize_success(self, config: LightTransformConfig) -> None:
        end_time = dt.datetime.now()
        execution_duration = (end_time - self.start_time).total_seconds()
        self.last_status = "success"
        self.last_error_type = None
        self.last_error_message = None

        if self.monitor:
            self.monitor.log_success(
                table_name=config.table_name,
                job_name=config.job_name,
                metadata={
                    "end_time": end_time.isoformat(),
                    "process_guid": self.process_guid,
                    "execution_duration_seconds": execution_duration,
                    "status": "completed_successfully",
                    "delta_optimized": True,
                    "spark_app_id": self.spark.sparkContext.applicationId if self.spark else None
                }
            )

        self.logger.info(
            f"✅ Light Transform completado exitosamente table: {config.table_name} "
            f"process_id: {self.process_id} process_guid: {self.process_guid} "
            f"duration: {execution_duration:.2f}s"
        )

    def finalize_warning(self, config: LightTransformConfig, warning_message: str, warnings: Optional[list] = None) -> None:
        end_time = dt.datetime.now()
        execution_duration = (end_time - self.start_time).total_seconds()
        warnings = warnings or []
        self.last_status = "warning"
        self.last_error_type = "Warning"
        self.last_error_message = warning_message

        if self.monitor:
            warning_metadata = {
                "warning_type": "transformation_warnings",
                "warnings_count": len(warnings),
                "warnings_detail": warnings[:5],
                "process_guid": self.process_guid,
                "execution_duration_seconds": execution_duration,
                "data_written": True,
                "spark_app_id": self.spark.sparkContext.applicationId if self.spark else None
            }
            self.monitor.log_warning(
                table_name=config.table_name,
                warning_message=warning_message,
                job_name=config.job_name,
                metadata=warning_metadata
            )

        self.logger.info("ℹ️ Job terminando como SUCCESS (con advertencias registradas)")

    def finalize_error(self, config: Optional[LightTransformConfig], error_message: str, error_type: str, extra_context: Optional[dict] = None) -> None:
        end_time = dt.datetime.now()
        execution_duration = (end_time - self.start_time).total_seconds()
        self.last_status = "error"
        self.last_error_type = error_type
        self.last_error_message = error_message
        context = {
            "error_type": error_type,
            "failed_at": end_time.isoformat(),
            "process_guid": self.process_guid,
            "execution_duration_before_failure": execution_duration,
            "spark_app_id": self.spark.sparkContext.applicationId if self.spark else None
        }
        if extra_context:
            context.update(extra_context)

        if self.monitor and config:
            self.monitor.log_error(
                table_name=config.table_name,
                error_message=error_message,
                job_name=config.job_name,
                metadata=context
            )

        self.logger.info("ℹ️ Job terminando como SUCCESS para evitar dobles notificaciones")

    def stop_spark(self) -> None:
        if self.spark:
            self.spark.stop()

    def run_with_config(self, config: LightTransformConfig, log_level: str = 'INFO') -> None:
        self.process_guid = str(uuid.uuid4())
        self.start_time = dt.datetime.now()
        self.logger = None
        self.last_status = "running"
        self.last_error_type = None
        self.last_error_message = None
        try:
            self.initialize_logging(config, log_level)
            self.initialize_monitoring(config)
            self.log_start(config)

            self.initialize_spark()
            self.s3_client = boto3.client('s3')
            processor_factory = self.build_processor(config)
            processor = processor_factory.create()
            processor.process_table(config)
            self.finalize_success(config)

        except TransformationWarningException as warning_exc:
            error_msg = str(warning_exc)
            if self.logger:
                self.logger.warning(
                    f"⚠️ Transformación completada con advertencias: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} warnings_count: {len(warning_exc.warnings) if hasattr(warning_exc, 'warnings') else 0}"
                )
            self.finalize_warning(config, error_msg, getattr(warning_exc, 'warnings', []))

        except TransformationException as trans_exc:
            error_msg = str(trans_exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error crítico de transformación: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} column: {trans_exc.column_name if hasattr(trans_exc, 'column_name') else 'unknown'}"
                )
            self.finalize_error(
                config,
                error_msg,
                "TransformationException",
                extra_context={
                    "error_column": trans_exc.column_name if hasattr(trans_exc, 'column_name') else 'unknown'
                }
            )

        except DataValidationException as validation_exc:
            error_msg = str(validation_exc)
            if self.logger:
                self.logger.warning(f"⚠️ Validación de datos: {error_msg} table: {config.table_name if config else 'unknown'}")

            if "empty table" in error_msg.lower() or "no data" in error_msg.lower():
                self.finalize_warning(config, error_msg, warnings=["empty_table"])
                if self.logger:
                    self.logger.info("ℹ️ Job terminando como SUCCESS - tabla vacía manejada correctamente")
            else:
                self.finalize_error(config, error_msg, "DataValidationException")

        except ConfigurationError as config_exc:
            error_msg = str(config_exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error de configuración: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} job: {config.job_name if config else 'unknown'}"
                )
            self.finalize_error(config, error_msg, "ConfigurationError")

        except WatermarkError as watermark_exc:
            error_msg = str(watermark_exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error manejando watermarks: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} job: {config.job_name if config else 'unknown'}"
                )
            self.finalize_error(config, error_msg, "WatermarkError")

        except MonitoringError as monitor_exc:
            error_msg = str(monitor_exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error en monitoreo: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} job: {config.job_name if config else 'unknown'}"
                )
            self.finalize_error(config, error_msg, "MonitoringError")

        except ProcessingError as proc_exc:
            error_msg = str(proc_exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error de procesamiento: {error_msg} "
                    f"table: {config.table_name if config else 'unknown'} job: {config.job_name if config else 'unknown'}"
                )
            self.finalize_error(config, error_msg, "ProcessingError")

        except Exception as exc:
            error_msg = str(exc)
            if self.logger:
                self.logger.error(
                    f"❌ Error en Light Transform: {error_msg} table: {config.table_name if config else 'unknown'} "
                    f"job: {config.job_name if config else 'unknown'} error_type: {type(exc).__name__} process_guid: {self.process_guid}"
                )
            self.finalize_error(config, error_msg, type(exc).__name__)

        finally:
            self.stop_spark()

    def run(self, argv: Any = None):
        argv = argv or sys.argv
        args = self.parse_arguments(argv)
        log_level = args.get('LOG_LEVEL', 'INFO')
        config = LightTransformConfigFactory.from_args(args)
        self.run_with_config(config, log_level)


__all__ = ["LightTransformOrchestrator"]

