"""
aje_libs - Biblioteca principal

Estrategia de importación:
- datalake: Cargado automáticamente (shared, extract_data)
- common: Carga explícita (lazy) - from aje_libs import common
- bd: Carga explícita (lazy) - from aje_libs import bd
- documents: Carga explícita (lazy) - from aje_libs import documents

Ejemplos:
    # Automático (datalake)
    from aje_libs.datalake.extract_data import DataExtractionOrchestrator
    
    # Lazy (common, bd, documents)
    from aje_libs import common
    from aje_libs.common.helpers import SecretsHelper
"""
# Cargar automáticamente solo datalake (módulo principal)
from . import datalake

__all__ = ['datalake', 'common', 'bd', 'documents']

# Lazy loading para módulos NO datalake
# Estos módulos solo se importan cuando se acceden explícitamente
def __getattr__(name: str):
    """
    Importación lazy para módulos que no son datalake.
    
    Permite importar módulos sin cargarlos automáticamente:
        from aje_libs import common  # Solo se carga cuando se accede
        from aje_libs import bd     # Solo se carga cuando se accede
        from aje_libs import documents  # Solo se carga cuando se accede
    """
    if name == 'common':
        from . import common
        return common
    elif name == 'bd':
        from . import bd
        return bd
    elif name == 'documents':
        from . import documents
        return documents
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
