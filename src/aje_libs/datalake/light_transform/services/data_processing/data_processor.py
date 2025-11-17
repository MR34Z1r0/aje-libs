"""
Procesador principal de datos para light_transform.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import pytz

from aje_libs.datalake.light_transform.contracts.configuration import IConfigurationProvider, ILightTransformConfig
from aje_libs.datalake.light_transform.contracts.data_processing import IDataLoader, ILightTransformProcessor
from aje_libs.datalake.light_transform.contracts.storage import IDataWriter
from aje_libs.datalake.light_transform.contracts.storage.write_strategy_interface import IWriteStrategy  # ✅ Nueva interfaz
from aje_libs.datalake.light_transform.strategies import WriteStrategyFactory  # ✅ Factory de estrategias
from aje_libs.datalake.light_transform.strategies.write_strategy_validator import WriteStrategyValidator  # ✅ Validador de estrategias
from aje_libs.datalake.light_transform.utils.table_existence_checker import TableExistenceChecker  # ✅ Checker agnóstico
from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConfigurationError,
    DataValidationError as DataValidationException,
    MonitoringError,
    ProcessingError,
    WatermarkError,
)
from aje_libs.datalake.shared.models import ColumnMetadata, TableConfig, EndpointConfig  # ✅ Movidos a shared/models
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger, DynamoDBLogger
from aje_libs.datalake.light_transform.services.watermark.dynamodb_watermark_helper import DynamoDBWatermarkHelper
from aje_libs.datalake.shared.models import LoadMode
from aje_libs.datalake.shared.utils.partition_formatter import PartitionFormatter

TZ_LIMA = pytz.timezone('America/Lima')


class DataProcessor(ILightTransformProcessor):
    """
    Procesador principal de datos optimizado con logging integrado.
    Utiliza estrategias de escritura modulares según load_type (SRP, OCP).
    """

    def __init__(
        self,
        spark,
        configuration_provider: IConfigurationProvider,
        transformation_engine,
        data_loader: IDataLoader,
        data_writer: IDataWriter,
        logger=None,
        table_format: str = 'delta',  # ✅ Formato de tabla para existencia checks
    ):
        self.spark = spark
        self.configuration_provider = configuration_provider
        self.transformation_engine = transformation_engine
        self.data_loader = data_loader
        self.data_writer = data_writer
        self.logger = logger or DataLakeLogger.get_logger(__name__)
        self.table_format = table_format  # ✅ Formato de tabla (delta, iceberg, etc.)
        self.strategy_validator = WriteStrategyValidator(logger=self.logger)  # ✅ Validador de estrategias

    def process_table(self, config: ILightTransformConfig):
        table_name = config.table_name
        self.logger.info(f"Procesando tabla {table_name}")

        table_config, endpoint_config, columns_metadata = self._load_configurations(config)

        load_type = table_config.load_type.lower()
        if load_type == 'incremental':
            watermark_ref = config.watermark_storage

            if not watermark_ref or not watermark_ref.location:
                error_message = (
                    f"❌ CONFIGURACIÓN REQUERIDA: La tabla {table_name} tiene LOAD_TYPE=incremental, "
                    "pero no se configuró un almacenamiento de watermarks válido."
                )
                self.logger.error(error_message)
                raise ConfigurationError(error_message)

            self.logger.info(
                "✅ Validación exitosa: tabla incremental %s con almacenamiento de watermarks %s:%s",
                table_name,
                watermark_ref.provider,
                watermark_ref.location,
            )

        paths = self._build_paths(config, table_config)
        source_path = paths['raw']
        stage_path = paths['stage']

        load_mode = config.load_mode or LoadMode.NORMAL
        if load_mode == LoadMode.RESET:
            self.logger.info("♻️ LOAD_MODE=reset detectado - limpiando estado previo antes de la carga")
            self._cleanup_previous_state(
                config=config,
                table_config=table_config,
                stage_path=stage_path,
            )

        if not self.data_loader.exists(source_path):
            self.logger.warning(f"⚠️ Ruta de datos no existe: {source_path}")
            raise DataValidationException(f"Source path does not exist: {source_path}")

        df_source = self.data_loader.load(source_path)

        df_transformed, errors = self.transformation_engine.apply_transformations(df_source, columns_metadata)
        if errors:
            self.logger.warning(f"Advertencias: {len(errors)}")

        df_processed = self.transformation_engine.apply_post_processing(df_transformed, columns_metadata)

        destination_path = paths['stage']
        partition_cols = [col.name for col in columns_metadata if col.is_partition]

        self.logger.info(f"🎯 Aplicando reglas de negocio - load_type: {load_type}, load_mode: {load_mode.value}")

        # ✅ Determinar estrategia de escritura usando WriteStrategyFactory (SRP, OCP)
        write_strategy = self._determine_write_strategy(load_type, load_mode)
        self.logger.info(f"📋 Estrategia seleccionada: {write_strategy.get_strategy_name()}")

        # ✅ Ejecutar estrategia de escritura con parámetros apropiados
        self._execute_write_strategy(
            write_strategy=write_strategy,
            df=df_processed,
            path=destination_path,
            partition_cols=partition_cols,
            columns_metadata=columns_metadata,
            table_config=table_config
        )

        self.logger.info("✅ Procesamiento completado")

        if load_type.lower() == 'incremental':
            partition_column = table_config.partition_column.strip() if table_config.partition_column else None

            if partition_column:
                self.logger.info(
                    f"🔍 Confirmando watermark: usando TABLE_NAME='{config.table_name}' "
                    f"PARTITION_COLUMN='{partition_column}' desde tables.csv"
                )
                self._confirm_pending_watermark(
                    config=config,
                    table_name=config.table_name,
                    partition_column=partition_column,
                )
            else:
                self.logger.warning(
                    f"⚠️ Tabla incremental {table_config.stage_table_name} sin PARTITION_COLUMN en tables.csv. "
                    f"Intentando buscar desde columns_metadata como fallback..."
                )
                fallback_partition_column = self._find_partition_column(columns_metadata)
                if fallback_partition_column:
                    self.logger.info(
                        f"🔍 Confirmando watermark (fallback): usando TABLE_NAME='{config.table_name}' "
                        f"PARTITION_COLUMN='{fallback_partition_column}' desde columns_metadata"
                    )
                    self._confirm_pending_watermark(
                        config=config,
                        table_name=config.table_name,
                        partition_column=fallback_partition_column,
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Tabla incremental {table_config.stage_table_name} sin columna de partición - "
                        f"no se confirmará watermark. Verifique PARTITION_COLUMN en tables.csv"
                    )

    def _load_configurations(self, config: ILightTransformConfig) -> (TableConfig, EndpointConfig, List[ColumnMetadata]):
        sources = config.config_sources

        tables_source = sources.get('tables')
        credentials_source = sources.get('credentials')
        columns_source = sources.get('columns')

        if not tables_source or not tables_source.location:
            raise ConfigurationError("Config source 'tables' es obligatorio para light_transform.")
        if not credentials_source or not credentials_source.location:
            raise ConfigurationError("Config source 'credentials' es obligatorio para light_transform.")
        if not columns_source or not columns_source.location:
            raise ConfigurationError("Config source 'columns' es obligatorio para light_transform.")

        table_config = self.configuration_provider.get_table_config(
            config.table_name,
            tables_source.location,
        )
        endpoint_config = self.configuration_provider.get_endpoint_config(
            config.endpoint_name,
            credentials_source.location,
        )
        columns_data = self.configuration_provider.get_columns_metadata(
            config.table_name,
            columns_source.location,
        )
        columns_metadata = self._process_columns_metadata(columns_data, config.table_name)
        return table_config, endpoint_config, columns_metadata

    def _process_columns_metadata(self, columns_data: List[Dict[str, Any]], table_name: str) -> List[ColumnMetadata]:
        columns_metadata: List[ColumnMetadata] = []

        for row in columns_data:
            if row.get('TABLE_NAME', '').upper() == table_name.upper():
                column_meta = ColumnMetadata(
                    name=row.get('COLUMN_NAME', ''),
                    column_id=int(row.get('COLUMN_ID', '0')),
                    data_type=row.get('NEW_DATA_TYPE', 'string'),
                    transformation=row.get('TRANSFORMATION', ''),
                    is_partition=row.get('IS_PARTITION', 'false').lower() in ['true', '1', 'yes', 'y', 't'],
                    is_id=row.get('IS_ID', '').upper() == 'T',
                    is_order_by=row.get('IS_ORDER_BY', '').upper() == 'T',
                    is_filter_date=row.get('IS_FILTER_DATE', '').upper() == 'T',
                    is_process_period=row.get('IS_PROCESS_PERIOD', '').upper() == 'T',
                )
                columns_metadata.append(column_meta)

        return columns_metadata

    def _normalize_base_path(self, storage_ref) -> str:
        base = storage_ref.location if storage_ref else ""
        if not base:
            return ""
        if storage_ref.provider == 's3' and not base.startswith('s3://'):
            base = f"s3://{base}"
        return base.rstrip('/')

    @staticmethod
    def _compose_path(base: str, relative: str) -> str:
        if not base:
            return relative
        if not relative:
            return base
        return f"{base.rstrip('/')}/{relative.lstrip('/')}"

    def _build_paths(self, config: ILightTransformConfig, table_config: TableConfig) -> Dict[str, str]:
        date_process = config.date_process
        if date_process:
            try:
                date_to_use = dt.datetime.strptime(date_process, '%Y-%m-%d')
                date_to_use = TZ_LIMA.localize(date_to_use)
            except ValueError:
                self.logger.warning(f"⚠️ Fecha inválida '{date_process}', usando fecha actual")
                date_to_use = dt.datetime.now(TZ_LIMA)
        else:
            date_to_use = dt.datetime.now(TZ_LIMA)
            self.logger.info(f"📅 DATE_PROCESS no proporcionado, usando fecha actual: {date_to_use.strftime('%Y-%m-%d %H:%M:%S')}")

        source_table_clean = table_config.source_table.split()[0] if ' ' in table_config.source_table else table_config.source_table

        partition_format = table_config.partition_format or "year={YYYY}/month={MM}/day={DD}"
        formatter = PartitionFormatter(partition_format)
        partition_path = formatter.format_path(date_to_use)

        day_route = f"{config.team}/{config.data_source}/{config.endpoint_name}/{source_table_clean}/{partition_path}/"

        raw_base = self._normalize_base_path(config.source_storage)
        stage_base = self._normalize_base_path(config.stage_storage)

        raw_path = self._compose_path(raw_base, day_route)
        stage_relative = f"{config.team}/{config.data_source}/{config.endpoint_name}/{config.table_name}/"
        stage_path = self._compose_path(stage_base, stage_relative)

        self.logger.info(f"📂 Ruta RAW construida: {raw_path}")
        self.logger.info(f"📂 Ruta STAGE construida: {stage_path}")

        return {
            'raw': raw_path,
            'stage': stage_path
        }

    def _cleanup_previous_state(
        self,
        config: ILightTransformConfig,
        table_config: TableConfig,
        stage_path: str,
    ) -> None:
        try:
            self.data_writer.cleanup(stage_path)
        except NotImplementedError:
            self.logger.warning("⚠️ El data_writer actual no implementa cleanup; se omite la limpieza de stage")
        except Exception as exc:
            error_msg = f"Error eliminando datos en stage ({stage_path}): {exc}"
            self.logger.error(error_msg, exc_info=True)
            raise ProcessingError(error_msg) from exc

        self._cleanup_previous_logs(config)
        self._cleanup_previous_watermarks(config, table_config)

    def _cleanup_previous_logs(self, config: ILightTransformConfig) -> None:
        log_storage = config.log_storage
        if not log_storage or not log_storage.location:
            self.logger.info("ℹ️ No se configuró almacenamiento de logs; se omite limpieza de logs")
            return

        if log_storage.provider != 'dynamodb':
            self.logger.info(
                "ℹ️ Limpieza de logs no soportada para provider '%s'; se omite",
                log_storage.provider,
            )
            return

        try:
            # ✅ Extraer múltiples notification ARNs desde notification_targets
            sns_topic_arns = {}
            if config.notification_targets:
                for event_type, target in config.notification_targets.items():
                    if target and target.provider == 'sns' and target.location:
                        sns_topic_arns[event_type] = target.location
            # ⚠️ Compatibilidad hacia atrás: Si notification_targets está vacío, usar notification_target
            elif config.notification_target and config.notification_target.provider == 'sns':
                sns_topic_arns['failed'] = config.notification_target.location
            
            dynamo_logger = DynamoDBLogger(
                table_name=log_storage.location,
                team=config.team,
                data_source=config.data_source,
                endpoint_name=config.endpoint_name,
                flow_name='light_transform',
                environment=config.environment,
                sns_topic_arn=None,  # ⚠️ DEPRECATED: Usar sns_topic_arns
                sns_topic_arns=sns_topic_arns if sns_topic_arns else None,  # ✅ Pasar múltiples ARNs
            )
            deleted = dynamo_logger.delete_logs(table_name=config.table_name)
            self.logger.info(
                "🧹 Limpieza de logs completada (%s) - registros eliminados: %s",
                log_storage.location,
                deleted,
            )
        except Exception as exc:
            error_msg = f"No se pudieron limpiar los logs en {log_storage.location}: {exc}"
            self.logger.warning(f"⚠️ {error_msg}", exc_info=True)
            raise MonitoringError(error_msg) from exc

    def _cleanup_previous_watermarks(
        self,
        config: ILightTransformConfig,
        table_config: TableConfig,
    ) -> None:
        watermark_ref = config.watermark_storage
        partition_column = table_config.partition_column

        if not watermark_ref or not watermark_ref.location:
            self.logger.info("ℹ️ No se configuró almacenamiento de watermarks; se omite limpieza de watermarks")
            return

        if watermark_ref.provider != 'dynamodb':
            self.logger.info(
                "ℹ️ Limpieza de watermarks no soportada para provider '%s'; se omite",
                watermark_ref.provider,
            )
            return

        if not partition_column:
            self.logger.warning(
                f"⚠️ Tabla {config.table_name} sin PARTITION_COLUMN; se omite limpieza de watermarks"
            )
            return

        try:
            helper = DynamoDBWatermarkHelper(
                table_name=watermark_ref.location,
                team=config.team,
                data_source=config.data_source,
                endpoint_name=config.endpoint_name,
                project_name=config.project_name,
                logger=self.logger,
            )
            deleted = helper.delete_watermarks(
                table_name=config.table_name,
                column_name=partition_column,
            )
            self.logger.info(
                "🧹 Limpieza de watermarks completada (%s) - registros eliminados: %s",
                watermark_ref.location,
                deleted,
            )
        except Exception as exc:
            error_msg = f"No se pudieron limpiar los watermarks en {watermark_ref.location}: {exc}"
            self.logger.warning(f"⚠️ {error_msg}", exc_info=True)
            raise WatermarkError(error_msg) from exc

    def _confirm_pending_watermark(self, config: ILightTransformConfig, table_name: str, partition_column: Optional[str]) -> None:
        if not partition_column:
            self.logger.warning(f"⚠️ No se puede confirmar watermark: no hay columna de partición para tabla {table_name}")
            return

        watermark_ref = config.watermark_storage
        project_name = config.project_name or 'datalake'
        team = config.team or ''
        data_source = config.data_source or ''
        endpoint_name = config.endpoint_name or ''

        self.logger.info(
            f"🔍 Confirmando watermark PENDING → CONFIRMED: "
            f"table_name={table_name}, partition_column={partition_column}, "
            f"project_name={project_name}, watermark_storage={watermark_ref.location if watermark_ref else 'N/A'}, team={team}, data_source={data_source}, endpoint_name={endpoint_name}"
        )

        if not watermark_ref or not watermark_ref.location:
            self.logger.warning("⚠️ No se puede confirmar watermark: no hay almacenamiento configurado")
            return

        if watermark_ref.provider != 'dynamodb':
            self.logger.info(
                "ℹ️ Confirmación de watermarks no soportada para provider '%s'; se omite",
                watermark_ref.provider,
            )
            return

        try:
            watermark_helper = DynamoDBWatermarkHelper(
                table_name=watermark_ref.location,
                team=team,
                data_source=data_source,
                endpoint_name=endpoint_name,
                project_name=project_name,
                logger=self.logger
            )

            pending_watermark = watermark_helper.get_last_pending_watermark(
                table_name=table_name,
                column_name=partition_column
            )

            if not pending_watermark:
                self.logger.info(f"ℹ️ No hay watermark PENDING para confirmar: {table_name}.{partition_column}")
                return

            success = watermark_helper.confirm_watermark(
                table_name=table_name,
                column_name=partition_column,
                timestamp=pending_watermark['timestamp'],
                additional_metadata={
                    'confirmed_by_transform': True,
                    'transform_timestamp': dt.datetime.now(TZ_LIMA).isoformat()
                }
            )

            if success:
                self.logger.info(
                    f"✅ Watermark confirmado exitosamente: {table_name}.{partition_column} = {pending_watermark['extracted_value']}"
                )
            else:
                self.logger.warning(f"⚠️ No se pudo confirmar watermark para {table_name}.{partition_column}")

        except Exception as exc:
            error_msg = f"Error al confirmar watermark: {exc}"
            self.logger.error(f"❌ {error_msg}", exc_info=True)
            raise WatermarkError(error_msg) from exc

    def _find_process_period_column(self, columns_metadata: List[ColumnMetadata]) -> Optional[str]:
        for col in columns_metadata:
            if getattr(col, 'is_process_period', False):
                self.logger.info(f"📅 Columna de período encontrada (marcada): {col.name}")
                return col.name

        period_patterns = ['process_period', 'periodo', 'period', 'fecha_proceso', 'processperiod']
        for col in columns_metadata:
            col_name_lower = col.name.lower()
            for pattern in period_patterns:
                if pattern in col_name_lower:
                    self.logger.info(f"📅 Columna de período encontrada (por nombre): {col.name}")
                    return col.name

        self.logger.warning("⚠️ No se encontró columna de período de proceso")
        return None

    def _find_partition_column(self, columns_metadata: List[ColumnMetadata]) -> Optional[str]:
        for col in columns_metadata:
            if col.is_order_by:
                self.logger.info(f"🔍 Columna de partición encontrada (IS_ORDER_BY): {col.name}")
                return col.name

        for col in columns_metadata:
            if col.is_filter_date:
                self.logger.info(f"🔍 Columna de partición encontrada (IS_FILTER_DATE): {col.name}")
                return col.name

        for col in columns_metadata:
            if col.is_partition:
                self.logger.info(f"🔍 Columna de partición encontrada (IS_PARTITION): {col.name}")
                return col.name

        for col in columns_metadata:
            if col.is_process_period:
                self.logger.info(f"🔍 Columna de partición encontrada (IS_PROCESS_PERIOD): {col.name}")
                return col.name

        self.logger.warning("⚠️ No se encontró columna de partición para watermark")
        return None
    
    def _determine_write_strategy(self, load_type: str, load_mode: LoadMode) -> IWriteStrategy:
        """
        Determina la estrategia de escritura según load_type y load_mode (SRP, OCP)
        
        Args:
            load_type: Tipo de carga de la tabla ('full', 'incremental', 'time_range', etc.)
            load_mode: Modo de carga (INITIAL, RESET, NORMAL, REPROCESS)
            
        Returns:
            Instancia de IWriteStrategy apropiada
        """
        # Si load_mode es INITIAL o RESET, siempre usar OVERWRITE (full load)
        if load_mode in [LoadMode.INITIAL, LoadMode.RESET]:
            self.logger.info(f"🆕 LOAD_MODE={load_mode.value} detectado - usando estrategia FullLoad (OVERWRITE)")
            return WriteStrategyFactory.create('full')
        
        # Para otros modos, usar estrategia según load_type
        return WriteStrategyFactory.create(load_type)
    
    def _execute_write_strategy(
        self,
        write_strategy: IWriteStrategy,
        df,
        path: str,
        partition_cols: Optional[List[str]],
        columns_metadata: List[ColumnMetadata],
        table_config: TableConfig
    ) -> None:
        """
        Ejecuta la estrategia de escritura con los parámetros apropiados (SRP, OCP)
        Incluye validación de requisitos antes de ejecutar
        
        Args:
            write_strategy: Estrategia de escritura a ejecutar
            df: DataFrame con los datos procesados
            path: Ruta de destino
            partition_cols: Columnas de partición
            columns_metadata: Metadatos de columnas
            table_config: Configuración de la tabla
        """
        # Verificar si la tabla existe (para estrategias que lo requieren)
        table_exists = TableExistenceChecker.table_exists(
            spark=self.spark,
            path=path,
            table_format=self.table_format
        )
        
        # ✅ Validar requisitos de la estrategia antes de ejecutar
        validation_result = self.strategy_validator.validate_strategy_requirements(
            write_strategy=write_strategy,
            columns_metadata=columns_metadata,
            table_exists=table_exists,
            df=df
        )
        
        # Mostrar advertencias si las hay
        for warning in validation_result.get('warnings', []):
            self.logger.warning(f"⚠️ {warning}")
        
        # Si hay errores críticos, lanzar excepción o usar fallback
        if validation_result.get('errors'):
            strategy_name = write_strategy.get_strategy_name()
            error_msg = f"Errores de validación para estrategia '{strategy_name}': {validation_result['errors']}"
            
            # Para time_range, si no hay period_column, usar APPEND como fallback
            if strategy_name == 'time_range' and 'columna de período' in str(validation_result['errors']).lower():
                self.logger.warning(f"⚠️ {error_msg}. Usando APPEND como fallback.")
                self.data_writer.append(df=df, path=path, partition_cols=partition_cols)
                return
            else:
                # Para otros casos, lanzar excepción
                from ...shared.exceptions import ConfigurationException
                raise ConfigurationException(error_msg)
        
        # Preparar parámetros según el tipo de estrategia
        strategy_name = write_strategy.get_strategy_name()
        kwargs = {}
        
        if strategy_name == 'incremental':
            # Estrategia incremental: usar metadatos de validación
            id_columns = validation_result['metadata'].get('id_columns', [])
            can_use_merge = validation_result['metadata'].get('can_use_merge', False)
            
            kwargs['id_columns'] = id_columns
            kwargs['table_exists'] = table_exists
            
            if can_use_merge:
                self.logger.info(f"🔄 Incremental MERGE usando columnas ID: {id_columns}")
            else:
                reason = "sin columnas ID" if not id_columns else "tabla no existe (primera carga)"
                self.logger.info(f"📝 Incremental APPEND ({reason})")
        
        elif strategy_name == 'time_range':
            # Estrategia time_range: usar metadatos de validación
            period_column = validation_result['metadata'].get('period_column')
            if period_column:
                try:
                    periods = [row[period_column] for row in df.select(period_column).distinct().collect()]
                    kwargs['period_column'] = period_column
                    kwargs['period_values'] = periods
                    self.logger.info(f"⏰ TIME_RANGE: DELETE + INSERT - columna: {period_column}, períodos: {periods}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Error extrayendo períodos: {e}. Usando APPEND como fallback.")
                    self.data_writer.append(df=df, path=path, partition_cols=partition_cols)
                    return
            else:
                # Fallback si no hay period_column
                self.logger.warning("⚠️ TIME_RANGE sin columna de período - usando APPEND como fallback")
                self.data_writer.append(df=df, path=path, partition_cols=partition_cols)
                return
        
        elif strategy_name == 'full_load':
            record_count = validation_result['metadata'].get('record_count', df.count() if df else 0)
            self.logger.info(f"📦 Full load OVERWRITE: {record_count} registros")
        
        # Ejecutar la estrategia
        write_strategy.execute(
            data_writer=self.data_writer,
            df=df,
            path=path,
            partition_cols=partition_cols,
            **kwargs
        )


__all__ = ["DataProcessor"]

