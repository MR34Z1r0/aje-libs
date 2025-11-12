"""
aje_libs - Biblioteca principal

Contiene módulos para datalake, bd, common, documents

Nota: Los módulos bd, common y documents no se importan automáticamente
para evitar dependencias innecesarias. Para usarlos, impórtalos explícitamente:
    from aje_libs import bd
    from aje_libs import common
    from aje_libs import documents
"""
# Exportar módulos principales
from . import datalake

# Los módulos bd, common y documents NO se importan automáticamente
# Deben importarse explícitamente cuando se necesiten

__all__ = ['datalake']
