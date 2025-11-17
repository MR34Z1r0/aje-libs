# -*- coding: utf-8 -*-
"""
Interface para factories de componentes (DIP - Dependency Inversion Principle)
"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ....extract_data.models import ExtractionConfig
    from ....shared.models import DatabaseConfig

from ....extract_data.contracts import IExtractor, ILoader, IExtractionStrategy
from ..monitoring import IMonitor
from ..watermark import IWatermarkStorage
from ..configuration import IConfigurationProvider


class IComponentFactory(ABC):
    """Interface para factories que crean componentes del proceso de extracción"""
    
    @abstractmethod
    def create_extractor(self, config: 'ExtractionConfig', database_config: Optional['DatabaseConfig'] = None) -> IExtractor:
        """
        Crea un extractor según la configuración
        
        Args:
            config: Configuración de extracción
            database_config: Configuración de base de datos (opcional, puede venir en config)
            
        Returns:
            Instancia de IExtractor configurada
        """
        pass
    
    @abstractmethod
    def create_loader(self, config: 'ExtractionConfig') -> ILoader:
        """
        Crea un loader según la configuración
        
        Args:
            config: Configuración de extracción
            
        Returns:
            Instancia de ILoader configurada
        """
        pass
    
    @abstractmethod
    def create_monitor(self, config: 'ExtractionConfig', process_guid: Optional[str] = None) -> Optional[IMonitor]:
        """
        Crea un monitor según la configuración
        
        Args:
            config: Configuración de extracción
            process_guid: GUID del proceso (opcional)
            
        Returns:
            Instancia de IMonitor configurada o None si no hay configuración de monitoreo
        """
        pass
    
    @abstractmethod
    def create_watermark_storage(self, config: 'ExtractionConfig') -> Optional[IWatermarkStorage]:
        """
        Crea un watermark storage según la configuración
        
        Args:
            config: Configuración de extracción
            
        Returns:
            Instancia de IWatermarkStorage configurada o None si no es necesario
        """
        pass
    
    @abstractmethod
    def create_strategy(
        self, 
        config: 'ExtractionConfig', 
        table_config,
        watermark_storage: Optional[IWatermarkStorage] = None
    ) -> IExtractionStrategy:
        """
        Crea una estrategia de extracción según la configuración
        
        Args:
            config: Configuración de extracción
            table_config: Configuración de tabla
            watermark_storage: Storage de watermarks (opcional)
            
        Returns:
            Instancia de IExtractionStrategy configurada
        """
        pass
    
    @abstractmethod
    def create_configuration_provider(self, config: 'ExtractionConfig'):
        """
        Crea un proveedor de configuración según la configuración
        
        Args:
            config: Configuración de extracción
            
        Returns:
            Instancia de IConfigurationProvider configurada
        """
        pass

