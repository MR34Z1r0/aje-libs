# -*- coding: utf-8 -*-
"""
Factory de componentes para extracción de datos (DIP - Dependency Inversion)
Implementa IComponentFactory para inyección de dependencias
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...shared.contracts.factories import IComponentFactory
    from ...shared.models import DatabaseConfig

from ..models.extraction_config import ExtractionConfig
from ..contracts import IExtractor, ILoader, IExtractionStrategy
from ...shared.contracts.monitoring import IMonitor
from ...shared.contracts.watermark import IWatermarkStorage
from ...shared.contracts.configuration import IConfigurationProvider
from ...shared.models import TableConfig, DatabaseConfig
from .extractor_factory import ExtractorFactory
from .loader_factory import LoaderFactory
from .watermark_factory import WatermarkStorageFactory
from .strategy_factory import StrategyFactory
from .configuration_provider_factory import ConfigurationProviderFactory
from ...shared.factories import MonitorFactory
from ...shared.services.logging import LoggerService


class DefaultComponentFactory:  # Implementa IComponentFactory (heredado no puede usarse por circular import)
    """Factory por defecto para crear componentes de extracción (DIP - implementa IComponentFactory)"""
    
    def __init__(self, name_logger: Optional[str] = None):
        """
        Inicializa el factory
        
        Args:
            name_logger: Nombre del logger (opcional)
        """
        self.logger = LoggerService.get_logger(name_logger or __name__)
    
    def create_extractor(self, config: ExtractionConfig, database_config: Optional[DatabaseConfig] = None) -> IExtractor:
        """Crea un extractor según la configuración"""
        db_config = database_config or (config.database_config if hasattr(config, 'database_config') and config.database_config else None)
        if not db_config:
            from ...shared.exceptions import ConfigurationException
            raise ConfigurationException("database_config is required to create extractor")
        
        self.logger.debug(f"Creando extractor para {db_config.db_type}")
        return ExtractorFactory.create(
            db_type=db_config.db_type,
            config=db_config,
            name_logger=f"{__name__}.extractor"
        )
    
    def create_loader(self, config: ExtractionConfig) -> ILoader:
        """Crea un loader según la configuración"""
        self.logger.debug(f"Creando loader: {config.loader_type} -> {config.formatter_type}")
        loader_config = self._build_loader_config(config)
        return LoaderFactory.create(
            loader_type=config.loader_type,
            output_format=config.formatter_type,
            **loader_config
        )
    
    def create_monitor(self, config: ExtractionConfig, process_guid: Optional[str] = None) -> Optional[IMonitor]:
        """Crea un monitor según la configuración"""
        if not config.monitoring:
            return None
        
        self.logger.debug(f"Creando monitor: {config.monitoring.provider}")
        
        # Extraer notification ARNs
        notification_arn = None
        sns_topic_arns = {}
        if config.notification_targets:
            for event_type, target in config.notification_targets.items():
                if target and target.provider == 'sns' and target.location:
                    sns_topic_arns[event_type] = target.location
            notification_arn = sns_topic_arns.get('failed')
        elif config.notification_target and config.notification_target.provider == 'sns':
            notification_arn = config.notification_target.location
            sns_topic_arns['failed'] = notification_arn
        
        monitor_config = {
            'table_name': config.monitoring.location,
            'team': config.team,
            'data_source': config.data_source,
            'endpoint_name': config.endpoint_name,
            'environment': config.environment,
            'sns_topic_arn': notification_arn,
            'sns_topic_arns': sns_topic_arns if sns_topic_arns else None,
            'process_guid': process_guid,
            'flow_name': 'extract_data',
            'event_logger_type': 'extract_data',
            'notification_provider': 'sns',
        }
        
        # Añadir región si está disponible
        if hasattr(config.monitoring, 'options') and config.monitoring.options.get('region'):
            monitor_config['region'] = config.monitoring.options['region']
        
        return MonitorFactory.create(
            monitor_type=config.monitoring.provider,
            logger=self.logger,
            **monitor_config
        )
    
    def create_watermark_storage(self, config: ExtractionConfig) -> Optional[IWatermarkStorage]:
        """Crea un watermark storage según la configuración"""
        if not config.watermark_storage:
            return None
        
        self.logger.debug(f"Creando watermark storage: {config.watermark_storage.provider}")
        
        watermark_config = self._build_watermark_config(config)
        storage_type = watermark_config.pop('storage_type', 'dynamodb')
        
        return WatermarkStorageFactory.create(
            storage_type=storage_type,
            enable_transactions=True,  # Por defecto habilitar transacciones
            **watermark_config
        )
    
    def create_strategy(
        self, 
        config: ExtractionConfig, 
        table_config: TableConfig,
        watermark_storage: Optional[IWatermarkStorage] = None,
        db_type: Optional[str] = None
    ) -> IExtractionStrategy:
        """
        Crea una estrategia de extracción según la configuración.
        
        Args:
            config: Configuración de extracción
            table_config: Configuración de tabla
            watermark_storage: Storage para watermarks (opcional)
            db_type: Tipo de base de datos para QueryBuilder (opcional)
        """
        self.logger.debug(f"Creando estrategia para tabla: {table_config.source_table}")
        return StrategyFactory.create(
            table_config=table_config,
            extraction_config=config,
            watermark_storage=watermark_storage,
            db_type=db_type
        )
    
    def create_configuration_provider(self, config: ExtractionConfig) -> IConfigurationProvider:
        """Crea un proveedor de configuración según la configuración"""
        source_type = "csv"
        if config.config_sources:
            first_source = next(iter(config.config_sources.values()), None)
            if first_source:
                source_type = first_source.provider
        
        self.logger.debug(f"Creando configuration provider: {source_type}")
        return ConfigurationProviderFactory.create(
            source_type=source_type,
            logger=self.logger
        )
    
    def _build_loader_config(self, config: ExtractionConfig) -> dict:
        """Construye la configuración para el loader"""
        loader_config = {}
        
        if config.raw_storage:
            if config.raw_storage.provider == 's3':
                # Extraer bucket de location (formato: s3://bucket o bucket/path)
                location = config.raw_storage.location
                if location.startswith('s3://'):
                    location = location[5:]
                bucket = location.split('/')[0] if '/' in location else location
                loader_config['bucket_name'] = bucket
                
                # Extraer región si está disponible
                if config.raw_storage.options and config.raw_storage.options.get('region'):
                    loader_config['region'] = config.raw_storage.options['region']
                elif hasattr(config, 'region'):
                    loader_config['region'] = config.region
        
        # Opciones de formatter
        loader_config['formatter_options'] = {}
        if hasattr(config, 'formatter_options'):
            loader_config['formatter_options'] = config.formatter_options
        
        return loader_config
    
    def _build_watermark_config(self, config: ExtractionConfig) -> dict:
        """Construye la configuración para watermark storage"""
        watermark_config = {}
        
        if config.watermark_storage:
            storage_type = config.watermark_storage.provider.lower()
            watermark_config['storage_type'] = storage_type
            
            if storage_type == 'dynamodb':
                # Extraer tabla de location
                table_name = config.watermark_storage.location
                if '/' in table_name:
                    table_name = table_name.split('/')[-1]
                watermark_config['table_name'] = table_name
                
                # Extraer región
                if config.watermark_storage.options and config.watermark_storage.options.get('region'):
                    watermark_config['region'] = config.watermark_storage.options['region']
            elif storage_type == 'csv':
                watermark_config['csv_file_path'] = config.watermark_storage.location
        
        # Metadata común
        watermark_config['project_name'] = config.data_source
        watermark_config['team'] = config.team
        watermark_config['data_source'] = config.data_source
        watermark_config['endpoint_name'] = config.endpoint_name
        
        return watermark_config

