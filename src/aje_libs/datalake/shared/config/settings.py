# -*- coding: utf-8 -*-
"""
Gestión centralizada de configuración para pipelines del datalake.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import boto3


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


class Settings:
    """Administra la configuración según el entorno (local, Glue, etc.)."""

    def __init__(
        self,
        force_glue: Optional[bool] = None,
        env_path: Optional[Union[str, Path]] = None,
    ):
        self._load_env_file(env_path)
        self.is_aws_glue = force_glue if force_glue is not None else self._detect_aws_glue()
        self.is_aws_s3 = self._detect_aws_s3()
        self._config = self._load_configuration()
        self._setup_aws_session()

    def _load_env_file(self, env_path: Optional[Union[str, Path]]) -> None:
        try:
            from dotenv import load_dotenv
        except ImportError:
            # Solo mostrar si realmente es necesario (cuando falte el .env)
            return

        # Si se proporciona una ruta explícita, usarla
        if env_path:
            path = Path(env_path).expanduser()
            if path.exists():
                try:
                    load_dotenv(path)
                    return
                except Exception as exc:
                    print(f"⚠️ Error al cargar .env desde {path}: {exc}")
            else:
                print(f"⚠️ No se encontró .env en: {path}")
            return

        # Buscar .env desde el directorio de trabajo actual hacia arriba
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            env_file = parent / ".env"
            if env_file.exists():
                try:
                    load_dotenv(env_file)
                    return
                except Exception as exc:
                    print(f"⚠️ Error al cargar .env desde {env_file}: {exc}")
                    continue

        # Como último recurso, intentar con DEFAULT_ENV_PATH
        if DEFAULT_ENV_PATH.exists():
            try:
                load_dotenv(DEFAULT_ENV_PATH)
                return
            except Exception as exc:
                print(f"⚠️ Error al cargar .env desde {DEFAULT_ENV_PATH}: {exc}")
                return

        # Solo mostrar error si no se encontró en ningún lugar
        print(f"⚠️ No se encontró archivo .env (buscado desde: {current_dir})")

    def _detect_aws_glue(self) -> bool:
        return "AWS_EXECUTION_ENV" in os.environ or "GLUE_VERSION" in os.environ

    def _detect_aws_s3(self) -> bool:
        return self.is_aws_glue or os.environ.get("USE_S3_CONFIG", "false").lower() == "true"

    def _setup_aws_session(self) -> None:
        try:
            region_name = self._config.get("REGION", "us-east-1")
            profile_name = self._config.get("AWS_PROFILE")

            if not self.is_aws_glue and profile_name:
                boto3.setup_default_session(profile_name=profile_name, region_name=region_name)
            elif not self.is_aws_glue:
                boto3.setup_default_session(region_name=region_name)
            # En Glue no se configura sesión explícitamente, usa IAM role automáticamente
        except Exception as exc:
            # Solo mostrar errores, no éxitos
            print(f"⚠️ Error al configurar sesión AWS: {exc}")

    def _load_configuration(self) -> Dict[str, Any]:
        if self.is_aws_glue:
            return self._load_glue_config()
        return self._load_local_config()

    def _load_glue_config(self) -> Dict[str, Any]:
        try:
            from awsglue.utils import getResolvedOptions
        except ImportError:
            # Fallback silencioso a configuración local
            return self._load_local_config()

        try:
            # Usar solo nombres genéricos
            args = getResolvedOptions(
                sys.argv,
                [
                    "raw_bucket",
                    "project_name",
                    "team",
                    "data_source",
                    "environment",
                    "region",
                    "logs_table",
                    "table_name",
                    "tables",
                    "credentials",
                    "columns",
                    "endpoint_name",
                    "topic_arn",
                ],
            )

            max_threads = int(args.get("max_threads", "6"))
            chunk_size = int(args.get("chunk_size", "1000000"))

            return {
                "raw_bucket": args.get("raw_bucket"),
                "project_name": args.get("project_name"),
                "team": args.get("team"),
                "data_source": args.get("data_source"),
                "environment": args.get("environment"),
                "region": args.get("region"),
                "logs_table": args.get("logs_table"),
                "table_name": args.get("table_name"),
                "tables": args.get("tables"),
                "credentials": args.get("credentials"),
                "columns": args.get("columns"),
                "endpoint_name": args.get("endpoint_name"),
                "topic_arn": args.get("topic_arn"),
                "max_threads": max_threads,
                "chunk_size": chunk_size,
                "output_format": args.get("output_format", "parquet"),
                "extractor_type": args.get("extractor_type", "sqlserver"),
                "loader_type": args.get("loader_type", "s3"),
                "monitor_type": args.get("monitor_type", "dynamodb"),
                "AWS_PROFILE": None,
            }
        except Exception as exc:
            # Fallback silencioso a configuración local en caso de error
            return self._load_local_config()

    def _require_env_vars(self, required_vars: list[str]) -> None:
        missing = [var for var in required_vars if os.getenv(var) is None]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {missing}. "
                "Verifica tu archivo .env o variables de entorno."
            )

    def _load_local_config(self) -> Dict[str, Any]:
        required = [
            "MAX_THREADS",
            "CHUNK_SIZE",
            "project_name",
            "team",
            "data_source",
            "REGION",
            "CONNECTION_TIMEOUT",
            "LOGIN_TIMEOUT",
            "MAX_RETRIES",
            "RETRY_DELAY",
            "CONNECTION_POOL_SIZE",
            "CONNECTION_POOL_RECYCLE",
        ]
        self._require_env_vars(required)

        return {
            "raw_bucket": os.getenv("raw_bucket"),
            "project_name": os.getenv("project_name"),
            "team": os.getenv("team"),
            "data_source": os.getenv("data_source"),
            "environment": os.getenv("environment"),
            "region": os.getenv("region"),
            "logs_table": os.getenv("logs_table"),
            "table_name": os.getenv("table_name", ""),
            "tables": os.getenv("tables"),
            "credentials": os.getenv("credentials"),
            "columns": os.getenv("columns"),
            "endpoint_name": os.getenv("endpoint_name"),
            "topic_arn": os.getenv("topic_arn"),
            "max_threads": int(os.getenv("max_threads", "6")),
            "chunk_size": int(os.getenv("chunk_size", "1000000")),
            "output_format": os.getenv("output_format", "parquet"),
            "extractor_type": os.getenv("extractor_type"),
            "LOADER_TYPE": os.getenv("LOADER_TYPE"),
            "monitor_type": os.getenv("monitor_type"),
            "AWS_PROFILE": os.getenv("AWS_PROFILE"),
            "WATERMARK_STORAGE_TYPE": os.getenv("WATERMARK_STORAGE_TYPE"),
            "WATERMARK_TABLE": os.getenv("WATERMARK_TABLE"),
            "WATERMARK_CSV_PATH": os.getenv("WATERMARK_CSV_PATH"),
            "WATERMARK_PG_CONNECTION": os.getenv("WATERMARK_PG_CONNECTION"),
            "WATERMARK_PG_SCHEMA": os.getenv("WATERMARK_PG_SCHEMA"),
            "CONNECTION_TIMEOUT": int(os.getenv("CONNECTION_TIMEOUT")),
            "LOGIN_TIMEOUT": int(os.getenv("LOGIN_TIMEOUT")),
            "MAX_RETRIES": int(os.getenv("MAX_RETRIES")),
            "RETRY_DELAY": int(os.getenv("RETRY_DELAY")),
            "USE_SQLALCHEMY": os.getenv("USE_SQLALCHEMY", "false").lower() == "true",
            "CONNECTION_POOL_SIZE": int(os.getenv("CONNECTION_POOL_SIZE")),
            "CONNECTION_POOL_RECYCLE": int(os.getenv("CONNECTION_POOL_RECYCLE")),
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()

    def update(self, updates: Dict[str, Any]) -> None:
        self._config.update(updates)


settings = Settings(force_glue=False)


