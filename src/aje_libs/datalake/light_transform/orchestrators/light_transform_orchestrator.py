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
    DefaultLightTransformComponentFactory,  # ✅ Nueva factory
)
from aje_libs.datalake.light_transform.models import LightTransformConfig
from aje_libs.datalake.light_transform.services import DataLakeLogger
from aje_libs.datalake.light_transform.contracts.factories import ILightTransformComponentFactory  # ✅ Nueva interfaz
from aje_libs.datalake.light_transform.contracts.data_processing import ILightTransformProcessor  # ✅ Importar interfaz
from aje_libs.datalake.light_transform.orchestrators.component_initializer import ComponentInitializer  # ✅ Nuevo inicializador
from aje_libs.datalake.shared.contracts.monitoring import IMonitor
from aje_libs.datalake.shared.services.logging import LoggerService
# Importar SparkConfigBuilder directamente (no desde shared.__init__ para evitar requerir pyspark en extract_data)
from aje_libs.datalake.shared.utils.spark_config_builder import SparkConfigBuilder  # ✅ Builder para configs de Spark

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

    def __init__(
        self,
        component_factory: Optional[ILightTransformComponentFactory] = None,  # ✅ Nueva inyección de dependencias
    ):
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
        
        # ✅ Inyección de dependencias: usar factory proporcionado o crear uno por defecto
        self.component_factory = component_factory or DefaultLightTransformComponentFactory(
            logger_name=f"{__name__}.factory"
        )

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
        """
        Inicializa el monitor usando el component factory (DIP - inyección de dependencias)
        """
        # ✅ Usar component factory para crear monitor (SRP - delegación de responsabilidades)
        self.monitor = self.component_factory.create_monitor(
            config=config,
            process_guid=self.process_guid
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

    def initialize_spark(self, table_format: str = 'delta') -> None:
        """
        Inicializa SparkSession con configuraciones específicas según el formato de tabla (OCP - extensible)
        
        Args:
            table_format: Formato de tabla ('delta', 'iceberg', etc.) - por defecto 'delta'
        """
        # ✅ Usar SparkConfigBuilder para configurar según el formato (OCP - extensible sin modificar)
        spark_builder = SparkConfigBuilder.configure_for_format(
            spark_builder=SparkSession.builder,
            table_format=table_format,
            logger=self.logger
        )
        
        self.spark = spark_builder.getOrCreate()

        # Configuraciones adicionales comunes
        self.spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        self.spark.sparkContext._jsc.hadoopConfiguration().set("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")

    def build_processor(self, config: LightTransformConfig) -> ILightTransformProcessor:
        """
        Construye el procesador usando el component factory (DIP - inyección de dependencias)
        """
        # ✅ Usar component factory para crear processor (SRP - delegación de responsabilidades)
        return self.component_factory.create_processor(
            config=config,
            spark=self.spark,
            s3_client=self.s3_client
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
        """
        Ejecuta el proceso de light transform con la configuración proporcionada (SRP - usa ComponentInitializer)
        """
        self.process_guid = str(uuid.uuid4())
        self.start_time = dt.datetime.now()
        self.logger = None
        self.last_status = "running"
        self.last_error_type = None
        self.last_error_message = None
        try:
            # 1. Inicializar logging
            self.initialize_logging(config, log_level)
            
            # 2. Inicializar Spark y S3 client (usar formato del config)
            table_format = config.data_writer_type if hasattr(config, 'data_writer_type') else 'delta'
            self.initialize_spark(table_format=table_format)
            self.s3_client = boto3.client('s3')
            
            # 3. ✅ Usar ComponentInitializer para inicializar componentes (SRP - separación de responsabilidades)
            initializer = ComponentInitializer(
                config=config,
                component_factory=self.component_factory,
                spark=self.spark,
                s3_client=self.s3_client,
                logger=self.logger
            )
            
            # Inicializar todos los componentes
            components = initializer.initialize_all(
                monitor=None,  # Se creará automáticamente si hay config
                process_guid=self.process_guid
            )
            
            # Asignar componentes inicializados
            processor = components['processor']
            self.monitor = components['monitor'] or self.monitor
            
            # 4. Log start
            self.log_start(config)
            
            # 5. Procesar tabla
            processor.process_table(config)
            
            # 6. Finalizar con éxito
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

