"""
Contratos (interfaces) para light_transform.
"""
from .configuration.light_transform_config_interface import ILightTransformConfig
from .data_processing.data_processor_interface import ILightTransformProcessor
from .transformation.transformation_engine_interface import ITransformationEngine
from .storage import IDataWriter
from .factories import ILightTransformComponentFactory  # ✅ Nueva interfaz

__all__ = [
    'ILightTransformConfig',
    'ILightTransformProcessor',
    'ITransformationEngine',
    'IDataWriter',
    'ILightTransformComponentFactory',  # ✅ Nueva interfaz
]

