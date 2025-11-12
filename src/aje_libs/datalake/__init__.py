"""
aje_libs.datalake - Módulo principal del datalake

Contiene los módulos compartidos, extract_data y light_transform.

Nota: light_transform no se importa automáticamente para evitar dependencias
innecesarias (pyspark). Para usarlo, impórtalo explícitamente:
    from aje_libs.datalake import light_transform
    # o
    from aje_libs.datalake.light_transform import LightTransformOrchestrator
"""
# Exportar módulos principales
from . import shared
from . import extract_data

# light_transform NO se importa automáticamente
# Debe importarse explícitamente cuando se necesite

__all__ = ['shared', 'extract_data']
