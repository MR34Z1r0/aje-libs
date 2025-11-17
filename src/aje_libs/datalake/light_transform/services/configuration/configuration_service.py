"""
Servicio de configuración - Implementa carga y validación de configuraciones desde distintas fuentes (SRP).
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Dict, List, Any

from aje_libs.datalake.light_transform.contracts.configuration import IConfigurationProvider
from aje_libs.datalake.shared.contracts.configuration import ICsvLoader
from aje_libs.datalake.shared.contracts.logging import ILogger
from aje_libs.datalake.shared.services import build_default_csv_loader
from aje_libs.datalake.shared.models import TableConfig, EndpointConfig
from aje_libs.datalake.shared.exceptions import (
    ConfigurationException as ConfigurationError,
    DataValidationError as DataValidationException,
)


class ConfigurationService(IConfigurationProvider):
    """Servicio de configuración con soporte para múltiples orígenes de CSV."""

    def __init__(
        self,
        csv_loader: ICsvLoader = None,
        logger: ILogger = None,
    ):
        """Inicializa el servicio.

        Args:
            csv_loader: Implementación de `ICsvLoader` para cargar CSV.
            logger: Logger opcional.
        """
        self.csv_loader = csv_loader or build_default_csv_loader()
        self.logger = logger

    def load_csv(self, path: str) -> List[Dict[str, str]]:
        """Carga un CSV desde el origen indicado y devuelve filas sanitizadas."""
        try:
            if self.logger:
                self.logger.info(f"Cargando CSV desde {path}")

            content = self.csv_loader.load(path)
            csv_data = []
            reader = csv.DictReader(StringIO(content), delimiter=';')
            for row in reader:
                sanitized_row = self._sanitize_csv_row(row)
                csv_data.append(sanitized_row)

            # Filtrar por STATUS='a' o 'A' para tables_* y columns_*
            # Solo considerar registros con STATUS='a' o 'A', ignorar los demás
            path_lower = path.lower()
            if 'tables' in path_lower or 'columns' in path_lower:
                filtered_data = []
                for row in csv_data:
                    status = str(row.get('STATUS', '')).strip().upper()
                    if status == 'A':
                        filtered_data.append(row)
                    elif self.logger:
                        self.logger.debug(f"Registro ignorado por STATUS='{row.get('STATUS', '')}' en {path}")
                csv_data = filtered_data
                if self.logger:
                    self.logger.info(f"Después de filtrar por STATUS='a': {len(csv_data)} filas desde {path}")

            if self.logger:
                self.logger.info(f"CSV cargado exitosamente: {len(csv_data)} filas")

            return csv_data
        except DataValidationException:
            raise
        except Exception as exc:
            error_msg = f"Error cargando CSV desde {path}: {exc}"
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            raise ConfigurationError(error_msg) from exc

    def _sanitize_csv_row(self, row: Dict[str, str]) -> Dict[str, str]:
        """Sanitiza una fila de CSV removiendo comillas."""
        sanitized = {}
        for key, value in row.items():
            if isinstance(value, str):
                clean_value = value.replace('"""', '"')
                if clean_value.startswith('"') and clean_value.endswith('"'):
                    clean_value = clean_value[1:-1]
                sanitized[key] = clean_value
            else:
                sanitized[key] = value
        return sanitized

    def get_table_config(self, table_name: str, tables_csv_path: str, **filters) -> TableConfig:
        """Obtiene configuración de una tabla específica."""
        tables_data = self.load_csv(tables_csv_path)

        for row in tables_data:
            if row.get('STAGE_TABLE_NAME', '').upper() == table_name.upper():
                return TableConfig(
                    stage_table_name=row.get('STAGE_TABLE_NAME', ''),
                    source_table=row.get('SOURCE_TABLE', ''),
                    source_table_type=row.get('SOURCE_TABLE_TYPE', 'm'),
                    load_type=row.get('LOAD_TYPE', ''),
                    delay_incremental_ini=row.get('DELAY_INCREMENTAL_INI', '-2'),
                    delay_incremental_end=row.get('DELAY_INCREMENTAL_END') or '0',
                    partition_format=row.get('PARTITION_FORMAT') or 'year={YYYY}/month={MM}/day={DD}/hour={HH}',
                    partition_column=row.get('PARTITION_COLUMN'),
                    partition_mode=row.get('PARTITION_MODE', 'AUTO'),
                    start_value=row.get('START_VALUE') or None,
                    end_value=row.get('END_VALUE') or None
                )

        raise ConfigurationError(f"Configuración de tabla no encontrada: {table_name}")

    def get_endpoint_config(self, endpoint_name: str, endpoints_csv_path: str, **filters) -> EndpointConfig:
        """Obtiene configuración de un endpoint específico."""
        endpoints_data = self.load_csv(endpoints_csv_path)

        for row in endpoints_data:
            if row.get('ENDPOINT_NAME', '').upper() == endpoint_name.upper():
                return EndpointConfig(
                    endpoint_name=row.get('ENDPOINT_NAME', ''),
                    environment=row.get('ENVIRONMENT', ''),
                    src_db_name=row.get('SRC_DB_NAME', ''),
                    src_server_name=row.get('SRC_SERVER_NAME', ''),
                    src_db_username=row.get('SRC_DB_USERNAME', '')
                )

        raise ConfigurationError(f"Configuración de endpoint no encontrada: {endpoint_name}")

    def get_columns_metadata(self, table_name: str, columns_csv_path: str, **filters) -> List[Dict[str, Any]]:
        """Obtiene metadatos de columnas para una tabla."""
        columns_data = self.load_csv(columns_csv_path)

        table_columns = [
            row for row in columns_data
            if row.get('STAGE_TABLE_NAME', '').upper() == table_name.upper()
        ]

        if self.logger:
            self.logger.info(f"Encontradas {len(table_columns)} columnas para tabla {table_name}")

        return table_columns

