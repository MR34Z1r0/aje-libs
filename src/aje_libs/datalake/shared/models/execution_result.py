"""
Resultado base de ejecución compartido
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class ExecutionResult:
    """Resultado base de ejecución de procesos"""
    success: bool
    execution_time_seconds: float
    start_time: datetime
    end_time: datetime
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

