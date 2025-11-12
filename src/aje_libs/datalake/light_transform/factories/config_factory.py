"""
Factory para construir configuraciones de Light Transform.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from aje_libs.datalake.light_transform.models import LightTransformConfig
from aje_libs.datalake.shared.models import LoadMode, ResourceRef


class LightTransformConfigFactory:
    """Factory responsable de construir `LightTransformConfig` a partir de argumentos."""

    @staticmethod
    def from_args(args: Dict[str, Any]) -> LightTransformConfig:
        """
        Construye `LightTransformConfig` a partir de un diccionario de argumentos (Glue/CLI).
        """
        required_keys = [
            'job_name', 'table_name', 'load_mode', 'project_name', 'team', 'data_source',
            'endpoint_name', 'environment', 'raw_bucket', 'stage_bucket', 'logs_table',
            'tables', 'credentials', 'columns'
        ]

        missing = [key for key in required_keys if not args.get(key)]
        if missing:
            raise ValueError(f"Missing required parameters for Light Transform config: {', '.join(missing)}")

        date_process: Optional[str] = args.get('date_process')
        if isinstance(date_process, str) and date_process.upper() == "NONE":
            date_process = None

        load_mode_value = args.get('load_mode', 'normal')
        load_mode = LoadMode.from_string(load_mode_value)
        monitor_type = args.get('monitor_type', 'dynamodb')
        config_source_type = args.get('config_source_type', 'csv')
        data_loader_type = args.get('data_loader_type', 'spark')
        data_writer_type = args.get('data_writer_type', 'delta')

        def build_storage_ref(provider: str, location: Optional[str]) -> Optional[ResourceRef]:
            if not location:
                return None
            provider = (provider or '').lower() or 's3'
            normalized = location
            if provider == 's3' and not normalized.startswith('s3://'):
                normalized = f"s3://{normalized}"
            return ResourceRef(provider=provider, location=normalized)

        source_storage = build_storage_ref(
            args.get('SOURCE_STORAGE_PROVIDER', 's3'),
            args.get('raw_bucket')
        )
        stage_storage = build_storage_ref(
            args.get('STAGE_STORAGE_PROVIDER', 's3'),
            args.get('stage_bucket')
        )
        log_storage = build_storage_ref(
            args.get('LOG_STORAGE_PROVIDER', 'dynamodb'),
            args.get('logs_table')
        )
        watermark_storage = build_storage_ref(
            args.get('WATERMARK_STORAGE_PROVIDER', 'dynamodb'),
            args.get('watermarks_table')
        )

        config_sources = {}
        tables_ref = build_storage_ref(
            args.get('TABLES_SOURCE_PROVIDER', 's3'),
            args.get('tables')
        )
        credentials_ref = build_storage_ref(
            args.get('CREDENTIALS_SOURCE_PROVIDER', 's3'),
            args.get('credentials')
        )
        columns_ref = build_storage_ref(
            args.get('COLUMNS_SOURCE_PROVIDER', 's3'),
            args.get('columns')
        )
        if tables_ref:
            config_sources['tables'] = tables_ref
        if credentials_ref:
            config_sources['credentials'] = credentials_ref
        if columns_ref:
            config_sources['columns'] = columns_ref

        notification_target = build_storage_ref(args.get('NOTIFICATION_PROVIDER', 'sns'), args.get('topic_arn'))

        return LightTransformConfig(
            job_name=args['job_name'],
            table_name=args['table_name'],
            load_mode=load_mode,
            date_process=date_process,
            project_name=args['project_name'],
            team=args['team'],
            data_source=args['data_source'],
            endpoint_name=args['endpoint_name'],
            environment=args['environment'],
            source_storage=source_storage,
            stage_storage=stage_storage,
            log_storage=log_storage,
            watermark_storage=watermark_storage,
            config_sources=config_sources,
            notification_target=notification_target,
            monitor_type=monitor_type.lower(),
            config_source_type=config_source_type.lower(),
            data_loader_type=data_loader_type.lower(),
            data_writer_type=data_writer_type.lower(),
        )


__all__ = ["LightTransformConfigFactory"]

