# En utils/extract_data_v2/models/extraction_config.py

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from aje_libs.datalake.shared.models import LoadMode

@dataclass
class ExtractionConfig:
    """Main extraction configuration"""
    # Campos obligatorios PRIMERO
    project_name: str
    team: str
    data_source: str
    endpoint_name: str
    environment: str
    table_name: str
    max_threads: int        # ← Movido aquí (obligatorio)
    chunk_size: int         # ← Movido aquí (obligatorio)
    load_mode: LoadMode = LoadMode.NORMAL
    
    # Campos opcionales DESPUÉS
    s3_raw_bucket: Optional[str] = None
    local_path: Optional[str] = None
    dynamo_logs_table: Optional[str] = None
    topic_arn: Optional[str] = None
    output_format: str = "parquet"
    execution_timestamp: Optional[str] = None
    monitor_type: str = "dynamodb"
    config_source_type: str = "csv"
    loader_type: str = "s3"
    formatter_type: str = "parquet"
    tables_config_source: str = ""
    credentials_config_source: str = ""
    columns_config_source: str = ""

    def __post_init__(self):
        """Validate required fields and set defaults"""
        if not all([self.project_name, self.team, self.data_source, 
                   self.endpoint_name, self.environment, self.table_name]):
            raise ValueError("All extraction configuration fields are required")
        
        # Establecer timestamp si no se proporcionó
        if self.execution_timestamp is None:
            self.execution_timestamp = datetime.now().isoformat()
