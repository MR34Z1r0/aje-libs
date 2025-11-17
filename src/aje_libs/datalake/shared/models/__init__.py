"""
Modelos compartidos del datalake
"""
from .watermark_status import WatermarkStatus
from .execution_result import ExecutionResult
from .process_metadata import ProcessMetadata
from .load_mode import LoadMode
from .table_config import TableConfig
from .endpoint_config import EndpointConfig
from .column_metadata import ColumnMetadata
from .resource_ref import ResourceRef
from .database_config import DatabaseConfig  # ✅ Movido desde extract_data/models
from .file_metadata import FileMetadata  # ✅ Movido desde extract_data/models

__all__ = [
    'WatermarkStatus',
    'ExecutionResult',
    'ProcessMetadata',
    'LoadMode',
    'TableConfig',
    'EndpointConfig',
    'ColumnMetadata',
    'ResourceRef',
    'DatabaseConfig',  # ✅ Movido desde extract_data/models
    'FileMetadata',  # ✅ Movido desde extract_data/models
]

