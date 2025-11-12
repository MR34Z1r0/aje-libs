"""
Metadatos de proceso compartidos
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class ProcessMetadata:
    """Metadatos compartidos de un proceso"""
    process_id: str
    process_guid: str
    table_name: str
    job_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None

