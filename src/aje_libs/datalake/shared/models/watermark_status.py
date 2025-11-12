"""
Estados de watermark compartidos
"""
from enum import Enum

class WatermarkStatus(Enum):
    """Estados posibles de un watermark"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ROLLBACK = "ROLLBACK"

