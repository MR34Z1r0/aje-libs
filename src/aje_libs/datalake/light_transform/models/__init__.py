"""Modelos específicos de light_transform."""

# ✅ Importar modelos compartidos desde shared (no reexportarlos aquí)
from aje_libs.datalake.shared.models import ColumnMetadata, EndpointConfig, TableConfig

from .light_transform_config import LightTransformConfig
from .light_transform_result import LightTransformResult


__all__ = [
    # ⚠️ ColumnMetadata, TableConfig, EndpointConfig NO se reexportan aquí - deben importarse desde aje_libs.datalake.shared.models
    'LightTransformConfig',
    'LightTransformResult',  # ✅ Modelo de resultado para light_transform
]
