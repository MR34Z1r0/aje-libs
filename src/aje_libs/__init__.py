"""
aje_libs - Biblioteca principal

Estrategia de importación:
- datalake: Cargado automáticamente (shared, extract_data, light_transform)
- common: Carga explícita (lazy) - from aje_libs import common

Ejemplos:
    # Automático (datalake)
    from aje_libs.datalake.extract_data import DataExtractionOrchestrator
    from aje_libs.datalake.light_transform import LightTransformOrchestrator
    
    # Lazy (common)
    from aje_libs import common
    from aje_libs.common.aws.helpers import SecretsHelper  # ✅ Usar nueva ubicación
    # O simplemente:
    from aje_libs.common import SecretsHelper  # ✅ Mejor opción
"""
# Cargar automáticamente solo datalake (módulo principal)
from . import datalake

__all__ = ['datalake', 'common']

# Lazy loading para módulos NO datalake
# Estos módulos solo se importan cuando se acceden explícitamente
def __getattr__(name: str):
    """
    Importación lazy para módulos que no son datalake.
    
    Permite importar módulos sin cargarlos automáticamente:
        from aje_libs import common  # Solo se carga cuando se accede
    """
    if name == 'common':
        from . import common
        return common
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
