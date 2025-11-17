# En utils/extract_data_v2/models/extraction_config.py

from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime

from aje_libs.datalake.shared.models import LoadMode, ResourceRef


@dataclass
class ExtractionConfig:
    """
    Configuración principal de extracción - completamente agnóstica a proveedores específicos.
    
    Usa ResourceRef como estándar (igual que LightTransformConfig) para mantener consistencia.
    
    Sigue principios SOLID:
    - Open/Closed: Extensible sin modificar (nuevos proveedores via ResourceRef)
    - Dependency Inversion: Depende de abstracciones (ResourceRef), no de implementaciones específicas
    """
    # Campos obligatorios
    project_name: str
    team: str
    data_source: str
    endpoint_name: str
    environment: str
    table_name: str
    max_threads: int
    chunk_size: int
    load_mode: LoadMode = LoadMode.NORMAL
    
    # Configuraciones genéricas usando ResourceRef (estándar unificado)
    raw_storage: Optional[ResourceRef] = None
    monitoring: Optional[ResourceRef] = None
    notification_target: Optional[ResourceRef] = None  # ⚠️ DEPRECATED: Usar notification_targets en su lugar (mantenido para compatibilidad)
    notification_targets: Dict[str, ResourceRef] = field(default_factory=dict)  # ✅ Dict con keys: 'failed', 'success', 'warning'
    watermark_storage: Optional[ResourceRef] = None  # Storage para watermarks (dynamodb, csv, etc.)
    config_sources: Dict[str, ResourceRef] = field(default_factory=dict)  # Dict con keys: 'tables', 'credentials', 'columns'
    
    # Configuración de procesamiento
    output_format: str = "parquet"
    loader_type: str = "s3"  # Tipo de loader a usar (puede ser diferente del storage)
    formatter_type: str = "parquet"
    execution_timestamp: Optional[str] = None

    def __post_init__(self):
        """Validate required fields and set defaults"""
        if not all([self.project_name, self.team, self.data_source, 
                   self.endpoint_name, self.environment, self.table_name]):
            raise ValueError("All extraction configuration fields are required")
        
        # ✅ Compatibilidad hacia atrás: Si notification_target existe pero notification_targets está vacío,
        # usar notification_target como "failed" en notification_targets
        if self.notification_target and not self.notification_targets:
            self.notification_targets = {"failed": self.notification_target}
        
        # Establecer timestamp si no se proporcionó
        if self.execution_timestamp is None:
            self.execution_timestamp = datetime.now().isoformat()
