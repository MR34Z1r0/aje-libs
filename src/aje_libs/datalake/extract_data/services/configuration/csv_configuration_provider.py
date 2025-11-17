"""
Proveedor de configuraciones basado en CSV para extract_data.
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List, Optional

from aje_libs.datalake.shared.contracts import ICsvLoader, IConfigurationProvider
from aje_libs.datalake.shared.contracts.logging import ILogger


class CsvExtractionConfigurationProvider(IConfigurationProvider):
    """Carga configuraciones desde CSV locales o en S3."""

    def __init__(self, csv_loader: ICsvLoader, logger: Optional[ILogger] = None):
        self.csv_loader = csv_loader
        self.logger = logger
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def get_table_config(self, table_name: str, tables_source: str, **filters) -> Dict[str, Any]:
        data = self._load_csv(tables_source)
        criteria = {"STAGE_TABLE_NAME": table_name}
        criteria.update({k: v for k, v in filters.items() if v is not None})
        return self._find_config_by_criteria(data, **criteria)

    def get_endpoint_config(self, endpoint_name: str, endpoints_source: str, **filters) -> Dict[str, Any]:
        data = self._load_csv(endpoints_source)
        criteria = {"ENDPOINT_NAME": endpoint_name}
        criteria.update({k: v for k, v in filters.items() if v is not None})
        return self._find_config_by_criteria(data, **criteria)

    def get_columns_metadata(self, table_name: str, columns_source: str, **filters) -> List[Dict[str, Any]]:
        data = self._load_csv(columns_source)
        criteria = {"TABLE_NAME": table_name}
        criteria.update({k: v for k, v in filters.items() if v is not None})
        return self._filter_configs(data, **criteria)

    # Helpers

    def _load_csv(self, path: str) -> List[Dict[str, Any]]:
        if path in self._cache:
            return self._cache[path]

        content = self.csv_loader.load(path)
        reader = csv.DictReader(StringIO(content), delimiter=';')
        rows: List[Dict[str, Any]] = []
        for row in reader:
            clean_row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
            rows.append(clean_row)

        # Filtrar por STATUS='a' o 'A' para tables_* y columns_*
        # Solo considerar registros con STATUS='a' o 'A', ignorar los demás
        path_lower = path.lower()
        if 'tables' in path_lower or 'columns' in path_lower:
            filtered_rows = []
            for row in rows:
                status = str(row.get('STATUS', '')).strip().upper()
                if status == 'A':
                    filtered_rows.append(row)
                elif self.logger:
                    self.logger.debug(f"Registro ignorado por STATUS='{row.get('STATUS', '')}' en {path}")
            rows = filtered_rows
            if self.logger:
                self.logger.debug(f"Después de filtrar por STATUS='a': {len(rows)} filas desde {path}")

        # Solo loguear en DEBUG - la información de carga de CSV no es crítica
        if self.logger:
            self.logger.debug(f"Cargadas {len(rows)} filas desde {path}")

        self._cache[path] = rows
        return rows

    def _find_config_by_criteria(self, data: List[Dict[str, Any]], **criteria) -> Dict[str, Any]:
        for row in data:
            if all(row.get(key, '').upper() == str(value).upper() for key, value in criteria.items()):
                return row
        raise ValueError(f"Configuración no encontrada con criterios: {criteria}")

    def _filter_configs(self, data: List[Dict[str, Any]], **criteria) -> List[Dict[str, Any]]:
        filtered = []
        for row in data:
            if all(row.get(key, '').upper() == str(value).upper() for key, value in criteria.items()):
                filtered.append(row)
        return filtered


__all__ = ["CsvExtractionConfigurationProvider"]

