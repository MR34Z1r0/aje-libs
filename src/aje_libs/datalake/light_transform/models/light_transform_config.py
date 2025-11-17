"""
Modelo de configuración para Light Transform.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from aje_libs.datalake.light_transform.contracts.configuration import ILightTransformConfig
from aje_libs.datalake.shared.models import LoadMode, ResourceRef


@dataclass(frozen=True)
class LightTransformConfig(ILightTransformConfig):
    """Configuración inmutable y desacoplada de proveedores para Light Transform."""

    job_name: str
    table_name: str
    load_mode: LoadMode
    date_process: Optional[str]
    project_name: str
    team: str
    data_source: str
    endpoint_name: str
    environment: str
    source_storage: ResourceRef
    stage_storage: ResourceRef
    log_storage: Optional[ResourceRef]
    watermark_storage: Optional[ResourceRef]
    config_sources: Dict[str, ResourceRef]
    notification_target: Optional[ResourceRef] = None  # ⚠️ DEPRECATED: Usar notification_targets en su lugar (mantenido para compatibilidad)
    notification_targets: Dict[str, ResourceRef] = field(default_factory=dict)  # ✅ Dict con keys: 'failed', 'success', 'warning'
    monitor_type: str = "dynamodb"
    config_source_type: str = "csv"
    data_loader_type: str = "spark"
    data_writer_type: str = "delta"

