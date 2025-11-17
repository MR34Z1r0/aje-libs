# strategies/base/__init__.py
from .extraction_strategy import ExtractionStrategy
from .strategy_types import ExtractionStrategyType
# ✅ ExtractionParams movido a shared/models para evitar dependencias circulares
# Importar desde shared para mantener compatibilidad
from ....shared.models import ExtractionParams

__all__ = ['ExtractionStrategy', 'ExtractionParams', 'ExtractionStrategyType']