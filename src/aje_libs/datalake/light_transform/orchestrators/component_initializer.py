# -*- coding: utf-8 -*-
"""
Inicializador de componentes para LightTransformOrchestrator (SRP - Single Responsibility)
Extrae la responsabilidad de inicialización de componentes
"""
from typing import Optional
from ..models import LightTransformConfig
from ..contracts.data_processing import ILightTransformProcessor
from ...shared.contracts.monitoring import IMonitor
from ..contracts.factories.component_factory_interface import ILightTransformComponentFactory
from ...shared.services.logging import LoggerService


class ComponentInitializer:
    """Inicializador de componentes para light transform (SRP - una sola responsabilidad)"""
    
    def __init__(
        self,
        config: LightTransformConfig,
        component_factory: ILightTransformComponentFactory,
        spark,
        s3_client=None,
        logger: Optional = None
    ):
        """
        Inicializa el inicializador de componentes
        
        Args:
            config: Configuración de light transform
            component_factory: Factory para crear componentes
            spark: SparkSession
            s3_client: Cliente S3 (opcional)
            logger: Logger (opcional)
        """
        self.config = config
        self.component_factory = component_factory
        self.spark = spark
        self.s3_client = s3_client
        self.logger = logger or LoggerService.get_logger(__name__)
        
        # Componentes que se inicializarán
        self.processor: Optional[ILightTransformProcessor] = None
        self.monitor: Optional[IMonitor] = None
    
    def initialize_all(
        self,
        monitor: Optional[IMonitor] = None,
        process_guid: Optional[str] = None
    ) -> dict:
        """
        Inicializa todos los componentes necesarios
        
        Args:
            monitor: Monitor (opcional, se crea si no se proporciona y hay config)
            process_guid: GUID del proceso (opcional)
            
        Returns:
            Dict con todos los componentes inicializados
        """
        self.logger.info("🔧 Inicializando componentes de Light Transform...")
        
        # 1. Processor
        self._initialize_processor()
        
        # 2. Monitor
        self._initialize_monitor(monitor, process_guid)
        
        self.logger.info("✅ Todos los componentes de Light Transform inicializados correctamente")
        
        return {
            'processor': self.processor,
            'monitor': self.monitor,
        }
    
    def _initialize_processor(self):
        """Inicializa el procesador"""
        self.logger.info(f"⚙️ Creando processor para tabla: {self.config.table_name}")
        self.processor = self.component_factory.create_processor(
            config=self.config,
            spark=self.spark,
            s3_client=self.s3_client
        )
        self.logger.info(f"✅ Processor inicializado: {self.config.data_loader_type} -> {self.config.data_writer_type}")
    
    def _initialize_monitor(self, monitor: Optional[IMonitor] = None, process_guid: Optional[str] = None):
        """Inicializa el monitor"""
        if monitor:
            self.monitor = monitor
            self.logger.debug("✅ Monitor proporcionado externamente")
        elif self.config.log_storage:
            self.monitor = self.component_factory.create_monitor(self.config, process_guid)
            if self.monitor:
                self.logger.info(f"✅ Monitor inicializado: {self.config.monitor_type}")
            else:
                self.logger.debug("ℹ️  Monitor no disponible")
        else:
            self.logger.debug("ℹ️  Monitor no configurado")

