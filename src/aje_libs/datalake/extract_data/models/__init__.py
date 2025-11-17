"""
Modelos específicos de extract_data
"""
from .extraction_config import ExtractionConfig
from .extraction_result import ExtractionResult
from aje_libs.datalake.shared.models import (
    TableConfig, 
    ColumnMetadata, 
    EndpointConfig, 
    ResourceRef,
    DatabaseConfig,  # ✅ Movido desde aquí a shared/models
    FileMetadata,  # ✅ Movido desde aquí a shared/models
)

__all__ = [
    'ExtractionConfig',
    'ExtractionResult',
    # ⚠️ DatabaseConfig y FileMetadata ya NO se reexportan aquí - deben importarse desde aje_libs.datalake.shared.models
    # ⚠️ LoadMode ya NO se reexporta aquí - debe importarse directamente desde aje_libs.datalake.shared.models
    'TableConfig',
    'ColumnMetadata',
    'EndpointConfig',
    'ResourceRef',
]
