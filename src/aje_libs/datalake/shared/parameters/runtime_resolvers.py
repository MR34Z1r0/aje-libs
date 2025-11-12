from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from aje_libs.datalake.shared.config import settings
except ImportError:
    settings = None


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parsea pares KEY=VALUE en un diccionario."""
    overrides: Dict[str, str] = {}
    for raw in pairs:
        if "=" not in raw:
            raise ValueError(f"Override inválido '{raw}', usa formato KEY=VALUE")
        key, value = raw.split("=", 1)
        overrides[key.strip()] = value.strip()
    return overrides


def build_resource_dict(
    provider: Optional[str],
    location: Optional[str],
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Construye un diccionario de referencia a un recurso configurable."""
    if not location:
        return None
    normalized_provider = (provider or "s3").lower()
    return {
        "provider": normalized_provider,
        "location": location,
        "options": options or {},
    }


class LocalRuntime:
    """Clase para obtener parámetros desde CLI y archivo .env en ejecución local."""

    def __init__(self, cli_args: Optional[Dict[str, Any]] = None, env: Optional[Dict[str, str]] = None) -> None:
        """
        Args:
            cli_args: Diccionario con argumentos desde CLI (ej: {"table": "mi_tabla", "mode": "normal"})
            env: Diccionario con variables de entorno (por defecto usa os.environ)
        """
        self.cli_args = cli_args or {}
        self.env = env if env is not None else dict(os.environ)

    def _pick_setting(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Intenta obtener el valor desde ENV y luego desde settings."""
        value = self.env.get(name)
        if value not in (None, ""):
            return value
        if settings:
            value = settings.get(name)
            if value not in (None, ""):
                return value
        return default

    def _pick_setting_with_fallback(self, generic_name: str, specific_name: str, default: Optional[str] = None) -> Optional[str]:
        """Intenta obtener el valor buscando primero el nombre genérico y luego el específico."""
        # Buscar primero el nombre genérico
        value = self._pick_setting(generic_name)
        if value not in (None, ""):
            return value
        # Si no se encuentra, buscar el nombre específico
        return self._pick_setting(specific_name, default)

    def _to_int(self, value: Any, fallback: int) -> int:
        """Convierte un valor a entero de forma segura."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un valor: primero desde CLI, luego desde .env."""
        # Prioridad: CLI > ENV
        if key in self.cli_args:
            value = self.cli_args[key]
            return str(value) if value is not None else default
        return self.env.get(key, default)

    def _get_with_fallback(self, generic_key: str, specific_key: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un valor buscando primero el nombre genérico y luego el específico."""
        # Buscar primero el nombre genérico (desde CLI o ENV)
        value = self._get(generic_key)
        if value not in (None, ""):
            return value
        # Si no se encuentra, buscar el nombre específico
        return self._get(specific_key, default)

    def _profile_local_csv(self) -> Dict[str, Any]:
        """Perfil de configuración para CSV local."""
        base_dir = self.env.get("LOCAL_CONFIG_DIR", "./artifacts/configuration/csv")
        return {
            "config_source_type": "csv",
            "tables_config_source": self.env.get(
                "TABLES_CONFIG_LOCAL", f"file://{base_dir}/tables.csv"
            ),
            "credentials_config_source": self.env.get(
                "CREDENTIALS_CONFIG_LOCAL", f"file://{base_dir}/credentials.csv"
            ),
            "columns_config_source": self.env.get(
                "COLUMNS_CONFIG_LOCAL", f"file://{base_dir}/columns.csv"
            ),
        }

    def _profile_s3_csv(self) -> Dict[str, Any]:
        """Perfil de configuración para CSV en S3."""
        return {
            "config_source_type": "csv",
            "tables_config_source": self._get("tables", ""),
            "credentials_config_source": self._get("credentials", ""),
            "columns_config_source": self._get("columns", ""),
        }

    def _load_runtime_defaults(self) -> Dict[str, Any]:
        """Carga valores por defecto para runtime local."""
        return {
            "project_name": self._pick_setting("project_name", "datalake"),
            "team": self._pick_setting("team", "data-team"),
            "data_source": self._pick_setting("data_source", "source"),
            "endpoint_name": self._pick_setting("endpoint_name", "endpoint"),
            "environment": self._pick_setting("environment", "LOCAL"),
            "s3_raw_bucket": self._pick_setting("raw_bucket"),
            "dynamo_logs_table": self._pick_setting("logs_table"),
            "topic_arn": self._pick_setting("topic_arn"),
            "max_threads": self._to_int(self._pick_setting("max_threads", "1"), 1),
            "chunk_size": self._to_int(self._pick_setting("chunk_size", "1000000"), 1_000_000),
            "output_format": self._pick_setting("output_format", "parquet"),
            "monitor_type": self._pick_setting("monitor_type", "dynamodb"),
            "config_source_type": self._pick_setting("config_source_type", "csv"),
            "loader_type": self._pick_setting("loader_type", "s3"),
            "formatter_type": self._pick_setting("formatter_type", "parquet"),
            "tables_config_source": self._pick_setting("tables"),
            "credentials_config_source": self._pick_setting("credentials"),
            "columns_config_source": self._pick_setting("columns"),
        }

    def _build_config_profile(self, name: str) -> Dict[str, Any]:
        """Construye un perfil de configuración."""
        profiles = {
            "local_csv": self._profile_local_csv,
            "s3_csv": self._profile_s3_csv,
        }
        if name not in profiles:
            from aje_libs.datalake.shared.exceptions.configuration_exception import (
                ConfigurationException,
            )
            raise ConfigurationException(f"Config profile '{name}' is not defined")
        return profiles[name]()

    def _get_all_overrides(self) -> Dict[str, Any]:
        """Retorna todos los overrides combinando CLI y ENV."""
        overrides: Dict[str, Any] = {}

        # Parámetros básicos desde CLI
        if "table" in self.cli_args:
            overrides["table_name"] = self.cli_args["table"]
        if "mode" in self.cli_args:
            overrides["load_mode"] = self.cli_args["mode"]

        # Parámetros desde CLI/ENV (usar solo nombres genéricos)
        overrides.update({
            "table_name": overrides.get("table_name") or self._get("table_name"),
            "load_mode": overrides.get("load_mode") or self._get("load_mode", "normal"),
            "project_name": self._get("project_name"),
            "team": self._get("team"),
            "data_source": self._get("data_source"),
            "endpoint_name": self._get("endpoint_name"),
            "environment": self._get("environment", "LOCAL"),
            "s3_raw_bucket": self._get("raw_bucket"),
            "dynamo_logs_table": self._get("logs_table"),
            "tables_config_source": self._get("tables"),
            "credentials_config_source": self._get("credentials"),
            "columns_config_source": self._get("columns"),
        })

        # Parámetros opcionales
        if self._get("topic_arn"):
            overrides["topic_arn"] = self._get("topic_arn")
        
        if self._get("monitor_type"):
            overrides["monitor_type"] = self._get("monitor_type")
        
        if self._get("config_source_type"):
            overrides["config_source_type"] = self._get("config_source_type")
        
        if self._get("loader_type"):
            overrides["loader_type"] = self._get("loader_type")
        
        if self._get("formatter_type"):
            overrides["formatter_type"] = self._get("formatter_type")
        
        if self._get("output_format"):
            overrides["output_format"] = self._get("output_format")
        
        max_threads = self._get("max_threads")
        if max_threads:
            overrides["max_threads"] = int(max_threads)  # type: ignore[arg-type]
        
        chunk_size = self._get("chunk_size")
        if chunk_size:
            overrides["chunk_size"] = int(chunk_size)  # type: ignore[arg-type]
        
        # Watermarks table (opcional)
        watermarks_table = self._get("watermarks_table")
        if watermarks_table:
            overrides["dynamo_watermarks_table"] = watermarks_table

        return overrides

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa lista para usar en extract_data."""
        from aje_libs.datalake.shared.exceptions.configuration_exception import (
            ConfigurationException,
        )

        # Obtener overrides
        overrides = self._get_all_overrides()

        # Validar campos requeridos
        missing = [
            key for key in ("table_name", "s3_raw_bucket", "dynamo_logs_table") if not overrides.get(key)
        ]
        if missing:
            raise ConfigurationException(
                f"Variables faltantes para ejecución local: {', '.join(missing)}"
            )

        # Parsear EXTRA_OVERRIDES si existe
        set_overrides: Dict[str, str] = {}
        extra = self._get("EXTRA_OVERRIDES")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        # Obtener perfil de configuración
        config_profile = self._get("config_profile", "local_csv")

        # Ensamblar configuración completa: defaults + perfil + overrides + set_overrides
        config = self._load_runtime_defaults()
        config.update(self._build_config_profile(config_profile))

        # Aplicar overrides
        for key, value in overrides.items():
            if value not in (None, ""):
                config[key] = value

        # Aplicar set_overrides (máxima prioridad)
        if set_overrides:
            for key, value in set_overrides.items():
                if value not in (None, ""):
                    config[key] = value

        # Agregar metadatos
        config["log_level"] = self._get("log_level", "INFO")
        dry_run_value = self._get("dry_run", "false")
        config["dry_run"] = str(dry_run_value).lower() in ("1", "true", "yes")

        return config


class GlueAWSRuntime:
    """Clase para obtener parámetros desde getResolvedOptions en AWS Glue."""

    def __init__(self, argv: List[str]) -> None:
        """
        Args:
            argv: Lista de argumentos del script (sys.argv)
        """
        self.argv = argv

    def get_resolved_options(self, required: List[str], optional: List[str]) -> Dict[str, str]:
        """Obtiene parámetros resueltos desde Glue."""
        try:
            from awsglue.utils import getResolvedOptions  # type: ignore
        except ImportError as exc:
            raise RuntimeError("getResolvedOptions no disponible fuera de AWS Glue") from exc

        optional_present = [key for key in optional if f"--{key}" in self.argv]
        return getResolvedOptions(self.argv, required + optional_present)

    def get_all_overrides(self) -> Dict[str, Any]:
        """Retorna todos los overrides desde los parámetros de Glue.
        
        Acepta nombres genéricos y específicos para compatibilidad.
        """
        # Usar solo nombres genéricos
        required = [
            "table_name",
            "load_mode",
            "project_name",
            "team",
            "data_source",
            "endpoint_name",
            "environment",
            "raw_bucket",
            "logs_table",
            "tables",
            "credentials",
            "columns",
        ]

        optional = [
            "config_profile",
            "monitor_type",
            "config_source_type",
            "loader_type",
            "formatter_type",
            "output_format",
            "topic_arn",
            "max_threads",
            "chunk_size",
            "log_level",
            "extra_overrides",
            "watermarks_table",
        ]

        params = self.get_resolved_options(required, optional)

        overrides: Dict[str, Any] = {
            "table_name": params.get("table_name"),
            "load_mode": params.get("load_mode", "normal"),
            "project_name": params.get("project_name"),
            "team": params.get("team"),
            "data_source": params.get("data_source"),
            "endpoint_name": params.get("endpoint_name"),
            "environment": params.get("environment"),
            "s3_raw_bucket": params.get("raw_bucket"),
            "dynamo_logs_table": params.get("logs_table"),
            "tables_config_source": params.get("tables"),
            "credentials_config_source": params.get("credentials"),
            "columns_config_source": params.get("columns"),
        }

        # Parámetros opcionales
        if params.get("topic_arn"):
            overrides["topic_arn"] = params.get("topic_arn")
        
        if params.get("monitor_type"):
            overrides["monitor_type"] = params.get("monitor_type")
        
        if params.get("config_source_type"):
            overrides["config_source_type"] = params.get("config_source_type")
        
        if params.get("loader_type"):
            overrides["loader_type"] = params.get("loader_type")
        
        if params.get("formatter_type"):
            overrides["formatter_type"] = params.get("formatter_type")
        
        if params.get("output_format"):
            overrides["output_format"] = params.get("output_format")
        
        if params.get("max_threads"):
            overrides["max_threads"] = int(params.get("max_threads"))
        
        if params.get("chunk_size"):
            overrides["chunk_size"] = int(params.get("chunk_size"))
        
        if params.get("watermarks_table"):
            overrides["dynamo_watermarks_table"] = params.get("watermarks_table")

        return overrides

    def _profile_s3_csv(self) -> Dict[str, Any]:
        """Perfil de configuración para CSV en S3."""
        try:
            params = self.get_resolved_options([], ["tables", "credentials", "columns"])
        except Exception:
            params = {}
        return {
            "config_source_type": "csv",
            "tables_config_source": params.get("tables", ""),
            "credentials_config_source": params.get("credentials", ""),
            "columns_config_source": params.get("columns", ""),
        }

    def _load_runtime_defaults(self) -> Dict[str, Any]:
        """Carga valores por defecto para runtime Glue."""
        params = self.get_resolved_options([], ["project_name", "team", "data_source", "endpoint_name", "environment"])
        return {
            "project_name": params.get("project_name", "datalake"),
            "team": params.get("team", "data-team"),
            "data_source": params.get("data_source", "source"),
            "endpoint_name": params.get("endpoint_name", "endpoint"),
            "environment": params.get("environment", "GLUE"),
            "max_threads": 1,
            "chunk_size": 1_000_000,
            "output_format": "parquet",
            "monitor_type": "dynamodb",
            "config_source_type": "csv",
            "loader_type": "s3",
            "formatter_type": "parquet",
        }

    def _build_config_profile(self, name: str) -> Dict[str, Any]:
        """Construye un perfil de configuración."""
        if name == "s3_csv":
            return self._profile_s3_csv()
        # Por defecto s3_csv en Glue
        return self._profile_s3_csv()

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa lista para usar en extract_data."""
        overrides = self.get_all_overrides()

        # Parsear EXTRA_OVERRIDES si existe
        set_overrides: Dict[str, str] = {}
        params = self.get_resolved_options([], ["EXTRA_OVERRIDES"])
        extra = params.get("EXTRA_OVERRIDES")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        # Obtener perfil de configuración
        params_all = self.get_resolved_options([], ["CONFIG_PROFILE", "LOG_LEVEL"])
        config_profile = params_all.get("CONFIG_PROFILE", "s3_csv")

        # Ensamblar configuración completa: defaults + perfil + overrides + set_overrides
        config = self._load_runtime_defaults()
        config.update(self._build_config_profile(config_profile))

        # Aplicar overrides
        for key, value in overrides.items():
            if value not in (None, ""):
                config[key] = value

        # Aplicar set_overrides (máxima prioridad)
        if set_overrides:
            for key, value in set_overrides.items():
                if value not in (None, ""):
                    config[key] = value

        # Agregar metadatos
        config["log_level"] = params_all.get("LOG_LEVEL", "INFO")
        config["dry_run"] = False

        return config


class DatabricksRuntime:
    """Clase para obtener parámetros desde variables de entorno en Databricks."""

    def __init__(self, env: Optional[Dict[str, str]] = None) -> None:
        """
        Args:
            env: Diccionario con variables de entorno (por defecto usa os.environ)
        """
        self.env = env if env is not None else dict(os.environ)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un valor desde variables de entorno."""
        value = self.env.get(key)
        if value in ("", None):
            return default
        return value

    def _get_with_fallback(self, generic_key: str, specific_key: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un valor buscando primero el nombre genérico y luego el específico."""
        value = self.get(generic_key)
        if value not in (None, ""):
            return value
        return self.get(specific_key, default)

    def get_all_overrides(self) -> Dict[str, Any]:
        """Retorna todos los overrides desde variables de entorno."""
        from aje_libs.datalake.shared.exceptions.configuration_exception import (
            ConfigurationException,
        )

        overrides: Dict[str, Any] = {
            "table_name": self._get_with_fallback("table_name", "TABLE_NAME"),
            "load_mode": self._get_with_fallback("load_mode", "LOAD_MODE", "normal"),
            "project_name": self._get_with_fallback("project_name", "PROJECT_NAME"),
            "team": self._get_with_fallback("team", "TEAM"),
            "data_source": self._get_with_fallback("data_source", "DATA_SOURCE"),
            "endpoint_name": self._get_with_fallback("endpoint_name", "ENDPOINT_NAME"),
            "environment": self._get_with_fallback("environment", "ENVIRONMENT", "DATABRICKS"),
            "s3_raw_bucket": self.get("raw_bucket"),
            "dynamo_logs_table": self.get("logs_table"),
            "tables_config_source": self.get("tables"),
            "credentials_config_source": self.get("credentials"),
            "columns_config_source": self.get("columns"),
        }

        if not overrides["table_name"]:
            raise ConfigurationException("table_name es obligatorio en Databricks")

        # Parámetros opcionales
        if self._get("topic_arn"):
            overrides["topic_arn"] = self._get("topic_arn")
        
        if self._get("monitor_type"):
            overrides["monitor_type"] = self._get("monitor_type")
        
        if self._get("config_source_type"):
            overrides["config_source_type"] = self._get("config_source_type")
        
        if self._get("loader_type"):
            overrides["loader_type"] = self._get("loader_type")
        
        if self._get("formatter_type"):
            overrides["formatter_type"] = self._get("formatter_type")
        
        if self._get("output_format"):
            overrides["output_format"] = self._get("output_format")
        
        max_threads = self._get("max_threads")
        if max_threads:
            overrides["max_threads"] = int(max_threads)  # type: ignore[arg-type]
        
        chunk_size = self._get("chunk_size")
        if chunk_size:
            overrides["chunk_size"] = int(chunk_size)  # type: ignore[arg-type]
        
        watermarks_table = self._get("watermarks_table")
        if watermarks_table:
            overrides["dynamo_watermarks_table"] = watermarks_table

        return overrides

    def _pick_setting(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Intenta obtener el valor desde ENV y luego desde settings."""
        value = self.env.get(name)
        if value not in (None, ""):
            return value
        if settings:
            value = settings.get(name)
            if value not in (None, ""):
                return value
        return default

    def _to_int(self, value: Any, fallback: int) -> int:
        """Convierte un valor a entero de forma segura."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _profile_s3_csv(self) -> Dict[str, Any]:
        """Perfil de configuración para CSV en S3."""
        return {
            "config_source_type": "csv",
            "tables_config_source": self._get("tables", ""),
            "credentials_config_source": self._get("credentials", ""),
            "columns_config_source": self._get("columns", ""),
        }

    def _pick_setting_with_fallback(self, generic_name: str, specific_name: str, default: Optional[str] = None) -> Optional[str]:
        """Intenta obtener el valor buscando primero el nombre genérico y luego el específico."""
        value = self._pick_setting(generic_name)
        if value not in (None, ""):
            return value
        return self._pick_setting(specific_name, default)

    def _load_runtime_defaults(self) -> Dict[str, Any]:
        """Carga valores por defecto para runtime Databricks."""
        return {
            "project_name": self._pick_setting("project_name", "datalake"),
            "team": self._pick_setting("team", "data-team"),
            "data_source": self._pick_setting("data_source", "source"),
            "endpoint_name": self._pick_setting("endpoint_name", "endpoint"),
            "environment": self._pick_setting("environment", "DATABRICKS"),
            "max_threads": self._to_int(self._pick_setting("max_threads", "1"), 1),
            "chunk_size": self._to_int(self._pick_setting("chunk_size", "1000000"), 1_000_000),
            "output_format": self._pick_setting("output_format", "parquet"),
            "monitor_type": self._pick_setting("monitor_type", "dynamodb"),
            "config_source_type": self._pick_setting("config_source_type", "csv"),
            "loader_type": self._pick_setting("loader_type", "s3"),
            "formatter_type": self._pick_setting("formatter_type", "parquet"),
        }

    def _build_config_profile(self, name: str) -> Dict[str, Any]:
        """Construye un perfil de configuración."""
        if name == "s3_csv":
            return self._profile_s3_csv()
        # Por defecto s3_csv en Databricks
        return self._profile_s3_csv()

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa lista para usar en extract_data."""
        overrides = self.get_all_overrides()

        # Parsear EXTRA_OVERRIDES si existe
        set_overrides: Dict[str, str] = {}
        extra = self.get("EXTRA_OVERRIDES")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        # Obtener perfil de configuración
        config_profile = self.get("CONFIG_PROFILE", "s3_csv")

        # Ensamblar configuración completa: defaults + perfil + overrides + set_overrides
        config = self._load_runtime_defaults()
        config.update(self._build_config_profile(config_profile))

        # Aplicar overrides
        for key, value in overrides.items():
            if value not in (None, ""):
                config[key] = value

        # Aplicar set_overrides (máxima prioridad)
        if set_overrides:
            for key, value in set_overrides.items():
                if value not in (None, ""):
                    config[key] = value

        # Agregar metadatos
        config["log_level"] = self.get("LOG_LEVEL", "INFO")
        config["dry_run"] = self.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

        return config


# ============================================================================
# Clases para Light Transform (mismo patrón, pero con parámetros diferentes)
# ============================================================================


class LightTransformLocalRuntime:
    """Clase para obtener parámetros desde CLI y .env para Light Transform en local."""

    def __init__(self, cli_args: Optional[Dict[str, Any]] = None, env: Optional[Dict[str, str]] = None) -> None:
        self.cli_args = cli_args or {}
        self.env = env if env is not None else dict(os.environ)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self.cli_args:
            value = self.cli_args[key]
            return str(value) if value is not None else default
        return self.env.get(key, default)

    def get_all_overrides(self) -> Dict[str, Any]:
        overrides: Dict[str, Any] = {}

        if "table" in self.cli_args:
            overrides["table_name"] = self.cli_args["table"]
        if "mode" in self.cli_args:
            overrides["load_mode"] = self.cli_args["mode"]
        if "job_name" in self.cli_args:
            overrides["job_name"] = self.cli_args["job_name"]

        overrides.update({
            "job_name": overrides.get("job_name") or self.get("job_name", "LOCAL_LIGHT_TRANSFORM"),
            "table_name": overrides.get("table_name") or self.get("table_name"),
            "load_mode": overrides.get("load_mode") or self.get("load_mode", "normal"),
            "project_name": self.get("project_name"),
            "team": self.get("team"),
            "data_source": self.get("data_source"),
            "endpoint_name": self.get("endpoint_name"),
            "environment": self.get("environment", "LOCAL"),
            "source_storage": build_resource_dict(
                self.get("SOURCE_STORAGE_PROVIDER", "s3"),
                self._get("raw_bucket"),
            ),
            "stage_storage": build_resource_dict(
                self.get("STAGE_STORAGE_PROVIDER", "s3"),
                self._get("stage_bucket"),
            ),
            "log_storage": build_resource_dict(
                self.get("LOG_STORAGE_PROVIDER", "dynamodb"),
                self._get("logs_table"),
            ),
            "watermark_storage": build_resource_dict(
                self.get("WATERMARK_STORAGE_PROVIDER", "dynamodb"),
                self._get("watermarks_table"),
            ),
            "config_sources": {
                "tables": build_resource_dict(
                    self.get("TABLES_SOURCE_PROVIDER", "file"),
                    self._get(
                        "tables",
                        f"file://{self.get('LOCAL_CONFIG_DIR', './artifacts/configuration/csv')}/tables.csv",
                    ),
                ),
                "credentials": build_resource_dict(
                    self.get("CREDENTIALS_SOURCE_PROVIDER", "file"),
                    self._get("credentials"),
                ),
                "columns": build_resource_dict(
                    self.get("COLUMNS_SOURCE_PROVIDER", "file"),
                    self._get("columns"),
                ),
            },
            "notification_target": build_resource_dict(
                self.get("NOTIFICATION_PROVIDER", "sns"),
                self.get("topic_arn"),
            ),
        })

        if self.get("date_process"):
            overrides["date_process"] = self.get("date_process")
        if self.get("monitor_type"):
            overrides["monitor_type"] = self.get("monitor_type")
        if self.get("config_source_type"):
            overrides["config_source_type"] = self.get("config_source_type")
        if self.get("data_loader_type"):
            overrides["data_loader_type"] = self.get("data_loader_type")
        if self.get("data_writer_type"):
            overrides["data_writer_type"] = self.get("data_writer_type")

        return overrides

    def get_config(self) -> Dict[str, Any]:
        overrides = self.get_all_overrides()

        missing = [
            key for key in ("table_name", "source_storage", "stage_storage") if not overrides.get(key)
        ]
        if missing:
            raise ValueError(
                f"Variables faltantes para Light Transform local: {', '.join(missing)}"
            )

        set_overrides: Dict[str, str] = {}
        extra = self.get("EXTRA_OVERRIDES")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        return {
            "runtime": self.get("RUNTIME", "local"),
            "config_profile": self.get("CONFIG_PROFILE", "local_csv"),
            "log_level": self.get("LOG_LEVEL", "INFO"),
            "overrides": overrides,
            "set_overrides": set_overrides,
        }


class LightTransformGlueAWSRuntime:
    """Clase para obtener parámetros desde getResolvedOptions para Light Transform en Glue."""

    def __init__(self, argv: List[str]) -> None:
        self.argv = argv

    def get_resolved_options(self, required: List[str], optional: List[str]) -> Dict[str, str]:
        try:
            from awsglue.utils import getResolvedOptions  # type: ignore
        except ImportError as exc:
            raise RuntimeError("getResolvedOptions no disponible fuera de AWS Glue") from exc

        optional_present = [key for key in optional if f"--{key}" in self.argv]
        return getResolvedOptions(self.argv, required + optional_present)

    def get_all_overrides(self) -> Dict[str, Any]:
        # Usar solo nombres genéricos
        required = [
            "job_name",
            "table_name",
            "load_mode",
            "project_name",
            "team",
            "data_source",
            "endpoint_name",
            "environment",
            "raw_bucket",
            "stage_bucket",
            "logs_table",
            "tables",
            "credentials",
            "columns",
        ]

        optional = [
            "config_profile",
            "date_process",
            "monitor_type",
            "config_source_type",
            "data_loader_type",
            "data_writer_type",
            "watermarks_table",
            "topic_arn",
            "log_level",
            "extra_overrides",
        ]

        params = self.get_resolved_options(required, optional)

        overrides: Dict[str, Any] = {
            "job_name": params.get("job_name"),
            "table_name": params.get("table_name"),
            "load_mode": params.get("load_mode", "normal"),
            "project_name": params.get("project_name"),
            "team": params.get("team"),
            "data_source": params.get("data_source"),
            "endpoint_name": params.get("endpoint_name"),
            "environment": params.get("environment"),
            "source_storage": build_resource_dict(
                params.get("SOURCE_STORAGE_PROVIDER", "s3"),
                params.get("raw_bucket")
            ),
            "stage_storage": build_resource_dict(
                params.get("STAGE_STORAGE_PROVIDER", "s3"),
                params.get("stage_bucket")
            ),
            "log_storage": build_resource_dict(
                params.get("LOG_STORAGE_PROVIDER", "dynamodb"),
                params.get("logs_table")
            ),
            "watermark_storage": build_resource_dict(
                params.get("WATERMARK_STORAGE_PROVIDER", "dynamodb"),
                params.get("watermarks_table"),
            ),
            "config_sources": {
                "tables": build_resource_dict(
                    params.get("TABLES_SOURCE_PROVIDER", "s3"),
                    params.get("tables")
                ),
                "credentials": build_resource_dict(
                    params.get("CREDENTIALS_SOURCE_PROVIDER", "s3"),
                    params.get("credentials")
                ),
                "columns": build_resource_dict(
                    params.get("COLUMNS_SOURCE_PROVIDER", "s3"),
                    params.get("columns")
                ),
            },
            "notification_target": build_resource_dict(
                params.get("NOTIFICATION_PROVIDER", "sns"),
                params.get("topic_arn"),
            ),
        }

        if params.get("date_process"):
            overrides["date_process"] = params.get("date_process")
        if params.get("monitor_type"):
            overrides["monitor_type"] = params.get("monitor_type")
        if params.get("config_source_type"):
            overrides["config_source_type"] = params.get("config_source_type")
        if params.get("data_loader_type"):
            overrides["data_loader_type"] = params.get("data_loader_type")
        if params.get("data_writer_type"):
            overrides["data_writer_type"] = params.get("data_writer_type")

        return overrides

    def get_config(self) -> Dict[str, Any]:
        overrides = self.get_all_overrides()

        set_overrides: Dict[str, str] = {}
        params_extra = self.get_resolved_options([], ["extra_overrides"])
        extra = params_extra.get("extra_overrides")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        params_all = self.get_resolved_options([], ["config_profile", "log_level"])

        return {
            "runtime": "glue",
            "config_profile": params_all.get("config_profile", "s3_csv"),
            "log_level": params_all.get("log_level", "INFO"),
            "overrides": overrides,
            "set_overrides": set_overrides,
        }


class LightTransformDatabricksRuntime:
    """Clase para obtener parámetros desde variables de entorno para Light Transform en Databricks."""

    def __init__(self, env: Optional[Dict[str, str]] = None) -> None:
        self.env = env if env is not None else dict(os.environ)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        value = self.env.get(key)
        if value in ("", None):
            return default
        return value

    def get_all_overrides(self) -> Dict[str, Any]:
        overrides: Dict[str, Any] = {
            "job_name": self.get("job_name", "DATABRICKS_LIGHT"),
            "table_name": self.get("table_name"),
            "load_mode": self.get("load_mode", "normal"),
            "project_name": self.get("project_name"),
            "team": self.get("team"),
            "data_source": self.get("data_source"),
            "endpoint_name": self.get("endpoint_name"),
            "environment": self.get("environment", "DATABRICKS"),
            "source_storage": build_resource_dict(
                self.get("SOURCE_STORAGE_PROVIDER", "s3"),
                self.get("raw_bucket")
            ),
            "stage_storage": build_resource_dict(
                self.get("STAGE_STORAGE_PROVIDER", "s3"),
                self.get("stage_bucket")
            ),
            "log_storage": build_resource_dict(
                self.get("LOG_STORAGE_PROVIDER", "dynamodb"),
                self.get("logs_table")
            ),
            "watermark_storage": build_resource_dict(
                self.get("WATERMARK_STORAGE_PROVIDER", "dynamodb"),
                self.get("watermarks_table"),
            ),
            "config_sources": {
                "tables": build_resource_dict(
                    self.get("TABLES_SOURCE_PROVIDER", "s3"),
                    self.get("tables")
                ),
                "credentials": build_resource_dict(
                    self.get("CREDENTIALS_SOURCE_PROVIDER", "s3"),
                    self.get("credentials")
                ),
                "columns": build_resource_dict(
                    self.get("COLUMNS_SOURCE_PROVIDER", "s3"),
                    self.get("columns")
                ),
            },
            "notification_target": build_resource_dict(
                self.get("NOTIFICATION_PROVIDER", "sns"), self.get("topic_arn")
            ),
        }

        if not overrides["table_name"]:
            raise ValueError("table_name es obligatorio en Databricks")

        if self.get("date_process"):
            overrides["date_process"] = self.get("date_process")
        if self.get("monitor_type"):
            overrides["monitor_type"] = self.get("monitor_type")
        if self.get("config_source_type"):
            overrides["config_source_type"] = self.get("config_source_type")
        if self.get("data_loader_type"):
            overrides["data_loader_type"] = self.get("data_loader_type")
        if self.get("data_writer_type"):
            overrides["data_writer_type"] = self.get("data_writer_type")

        return overrides

    def get_config(self) -> Dict[str, Any]:
        overrides = self.get_all_overrides()

        set_overrides: Dict[str, str] = {}
        extra = self.get("extra_overrides")
        if extra:
            pieces = [piece.strip() for piece in extra.split(",") if piece.strip()]
            set_overrides = parse_key_value_pairs(pieces)

        return {
            "runtime": "databricks",
            "config_profile": self.get("config_profile", "s3_csv"),
            "log_level": self.get("log_level", "INFO"),
            "overrides": overrides,
            "set_overrides": set_overrides,
        }
