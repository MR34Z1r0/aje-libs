# -*- coding: utf-8 -*-
"""
Interface para factories de componentes de Light Transform (DIP - Dependency Inversion Principle)
"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import LightTransformConfig

from ...contracts.data_processing import ILightTransformProcessor
from ...shared.contracts.monitoring import IMonitor


class ILightTransformComponentFactory(ABC):
    """Interface para factories que crean componentes del proceso de light transform"""
    
    @abstractmethod
    def create_processor(self, config: 'LightTransformConfig', spark, s3_client=None) -> ILightTransformProcessor:
        """
        Crea un procesador de light transform según la configuración
        
        Args:
            config: Configuración de light transform
            spark: SparkSession
            s3_client: Cliente S3 (opcional)
            
        Returns:
            Instancia de ILightTransformProcessor configurada
        """
        pass
    
    @abstractmethod
    def create_monitor(self, config: 'LightTransformConfig', process_guid: Optional[str] = None) -> Optional[IMonitor]:
        """
        Crea un monitor según la configuración
        
        Args:
            config: Configuración de light transform
            process_guid: GUID del proceso (opcional)
            
        Returns:
            Instancia de IMonitor configurada o None si no hay configuración de monitoreo
        """
        pass

