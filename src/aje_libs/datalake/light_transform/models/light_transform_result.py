# -*- coding: utf-8 -*-
"""
Modelo de resultado para Light Transform.
Similar a ExtractionResult pero específico para transformaciones.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


@dataclass
class LightTransformResult:
    """Resultado de operación de light transform"""
    success: bool
    table_name: str
    records_processed: int
    files_processed: List[str]  # Archivos procesados/escritos
    execution_time_seconds: float
    load_mode: str  # Modo de carga utilizado
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    files_metadata: Optional[List[Dict[str, Any]]] = None  # Metadata de archivos generados
    transformation_stats: Optional[Dict[str, Any]] = None  # Estadísticas de transformación
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logging"""
        return {
            'success': self.success,
            'table_name': self.table_name,
            'records_processed': self.records_processed,
            'files_processed': self.files_processed,
            'execution_time_seconds': self.execution_time_seconds,
            'load_mode': self.load_mode,
            'error_message': self.error_message,
            'warning_message': self.warning_message,
            'metadata': self.metadata,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'files_metadata': self.files_metadata,
            'transformation_stats': self.transformation_stats
        }
    
    def get_total_size_mb(self) -> Decimal:
        """Obtener tamaño total de todos los archivos en MB"""
        if not self.files_metadata:
            return Decimal('0.0')
        total = sum(
            Decimal(str(f.get('file_size_mb', 0))) 
            if isinstance(f.get('file_size_mb', 0), (int, float)) 
            else f.get('file_size_mb', Decimal('0.0'))
            for f in self.files_metadata
        )
        return total
    
    def get_average_file_size_mb(self) -> Decimal:
        """Obtener tamaño promedio de archivos en MB"""
        if not self.files_metadata or len(self.files_metadata) == 0:
            return Decimal('0.0')
        total = self.get_total_size_mb()
        return total / Decimal(str(len(self.files_metadata)))

