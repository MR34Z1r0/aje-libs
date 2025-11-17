# -*- coding: utf-8 -*-
"""
Inicializador de componentes para ExtractionOrchestrator (SRP - Single Responsibility)
Extrae la responsabilidad de inicialización de componentes
"""
from typing import Optional
from ..models.extraction_config import ExtractionConfig
from ..contracts import IExtractor, ILoader, IExtractionStrategy
from ...shared.contracts.monitoring import IMonitor
from ...shared.contracts.watermark import IWatermarkStorage
from ...shared.contracts.configuration import IConfigurationProvider
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...shared.contracts.factories import IComponentFactory
from ...shared.models import TableConfig, DatabaseConfig
from ...shared.services.logging import LoggerService


class ComponentInitializer:
    """Inicializador de componentes para extracción (SRP - una sola responsabilidad)"""
    
    def __init__(
        self,
        config: ExtractionConfig,
        component_factory: 'IComponentFactory',
        logger: Optional = None
    ):
        """
        Inicializa el inicializador de componentes
        
        Args:
            config: Configuración de extracción
            component_factory: Factory para crear componentes
            logger: Logger (opcional)
        """
        self.config = config
        self.component_factory = component_factory
        self.logger = logger or LoggerService.get_logger(__name__)
        
        # Componentes que se inicializarán
        self.extractor: Optional[IExtractor] = None
        self.loader: Optional[ILoader] = None
        self.monitor: Optional[IMonitor] = None
        self.watermark_storage: Optional[IWatermarkStorage] = None
        self.strategy: Optional[IExtractionStrategy] = None
        self.configuration_provider: Optional[IConfigurationProvider] = None
        self.table_config: Optional[TableConfig] = None
        self.database_config: Optional[DatabaseConfig] = None
    
    def initialize_all(
        self,
        configuration_provider: Optional[IConfigurationProvider] = None,
        monitor: Optional[IMonitor] = None,
        process_guid: Optional[str] = None
    ) -> dict:
        """
        Inicializa todos los componentes necesarios
        
        Args:
            configuration_provider: Proveedor de configuración (opcional, se crea si no se proporciona)
            monitor: Monitor (opcional, se crea si no se proporciona y hay config)
            process_guid: GUID del proceso (opcional)
            
        Returns:
            Dict con todos los componentes inicializados
        """
        self.logger.info("🔧 Inicializando componentes...")
        
        # 1. Configuration Provider
        self._initialize_configuration_provider(configuration_provider)
        
        # 2. Load configurations
        self._load_configurations()
        
        # 3. Extractor
        self._initialize_extractor()
        
        # 4. Watermark Storage (solo si es necesario)
        self._initialize_watermark_storage()
        
        # 5. Loader
        self._initialize_loader()
        
        # 6. Monitor
        self._initialize_monitor(monitor, process_guid)
        
        # 7. Strategy
        self._initialize_strategy()
        
        self.logger.info("✅ Todos los componentes inicializados correctamente")
        
        return {
            'extractor': self.extractor,
            'loader': self.loader,
            'monitor': self.monitor,
            'watermark_storage': self.watermark_storage,
            'strategy': self.strategy,
            'configuration_provider': self.configuration_provider,
            'table_config': self.table_config,
            'database_config': self.database_config,
        }
    
    def _initialize_configuration_provider(self, provider: Optional[IConfigurationProvider] = None):
        """Inicializa el proveedor de configuración"""
        if provider:
            self.configuration_provider = provider
            self.logger.debug("✅ Configuration Provider proporcionado externamente")
        else:
            self.configuration_provider = self.component_factory.create_configuration_provider(self.config)
            self.logger.debug("✅ Configuration Provider creado")
    
    def _load_configurations(self):
        """Carga las configuraciones de tabla y base de datos"""
        self.logger.info("📂 Cargando configuraciones de tabla y base de datos...")
        
        # Usar config_sources desde ExtractionConfig
        tables_ref = self.config.config_sources.get("tables") if self.config.config_sources else None
        credentials_ref = self.config.config_sources.get("credentials") if self.config.config_sources else None
        columns_ref = self.config.config_sources.get("columns") if self.config.config_sources else None
        
        if not tables_ref:
            from ...shared.exceptions import ConfigurationException as ConfigurationError
            raise ConfigurationError(
                "config_sources['tables'] debe estar configurado en ExtractionConfig. "
                "No se pueden usar variables de entorno como fallback."
            )
        
        tables_source = tables_ref.location
        credentials_source = credentials_ref.location if credentials_ref else None
        columns_source = columns_ref.location if columns_ref else None
        
        # Cargar configuraciones usando el provider (igual que extraction_orchestrator)
        # Usar get_table_config (singular) en lugar de get_table_configs (plural)
        # No pasar ENV como filtro si no es necesario (igual que extraction_orchestrator)
        table_row = self.configuration_provider.get_table_config(
            self.config.table_name,
            tables_source
        )
        
        # Construir TableConfig usando el método helper (igual que extraction_orchestrator)
        self.table_config = self._build_table_config(table_row)
        
        # Cargar configuración de base de datos
        if credentials_source:
            # Usar get_endpoint_config (igual que extraction_orchestrator)
            # Pasar ENV solo si está disponible (igual que extraction_orchestrator)
            if hasattr(self.config, 'environment') and self.config.environment:
                db_row = self.configuration_provider.get_endpoint_config(
                    self.config.endpoint_name,
                    credentials_source,
                    ENV=self.config.environment,
                )
            else:
                db_row = self.configuration_provider.get_endpoint_config(
                    self.config.endpoint_name,
                    credentials_source
                )
            
            # Construir DatabaseConfig usando el builder (igual que extraction_orchestrator)
            # Construir el nombre del secreto usando el formato: {environment}/{project}/{team}/{data_source}
            secret_name = f"{self.config.environment.lower()}/{self.config.project_name}/{self.config.team}/{self.config.data_source}"
            
            from ...shared.builders import DatabaseConfigBuilder
            builder = DatabaseConfigBuilder.create()
            
            # Mapear campos del CSV al builder
            db_row_mapped = {
                'ENDPOINT_NAME': db_row.get('ENDPOINT_NAME', ''),
                'BD_TYPE': db_row.get('BD_TYPE', ''),
                'SRC_SERVER_NAME': db_row.get('SRC_SERVER_NAME', ''),
                'SRC_DB_NAME': db_row.get('SRC_DB_NAME', ''),
                'SRC_DB_USERNAME': db_row.get('SRC_DB_USERNAME', ''),
                'SRC_DB_SECRET': db_row.get('SRC_DB_SECRET', ''),
                'DB_PORT_NUMBER': db_row.get('DB_PORT_NUMBER'),
                'SECRET_NAME': secret_name,  # ✅ Usar formato construido: dev/datalake/apdayc/bigmagic
                'SECRET_KEY': db_row.get('SRC_DB_SECRET', ''),
            }
            
            self.database_config = builder.from_dict(db_row_mapped).build()
        
        # Asignar database_config al config para que esté disponible
        self.config.database_config = self.database_config
        
        self.logger.info(
            f"✅ Configuraciones cargadas - Tabla: {self.table_config.source_schema}.{self.table_config.source_table} | "
            f"Load Type: {self.table_config.load_type}, Partition Mode: {self.table_config.partition_mode}"
        )
    
    def _initialize_extractor(self):
        """Inicializa el extractor"""
        self.logger.info(f"🔌 Creando extractor para {self.database_config.db_type}...")
        self.extractor = self.component_factory.create_extractor(self.config, self.database_config)
        
        # Test database connection
        self.logger.info("🔍 Probando conexión a base de datos...")
        if not self.extractor.test_connection():
            from ...shared.exceptions import ConfigurationException as ConnectionError
            raise ConnectionError("Failed to connect to database")
        self.logger.info("✅ Conexión a base de datos exitosa")
    
    def _initialize_watermark_storage(self):
        """Inicializa el watermark storage si es necesario"""
        strategy_needs_watermark = self._strategy_needs_watermark_storage()
        
        if strategy_needs_watermark:
            self.logger.info("💾 Inicializando watermark storage...")
            self.watermark_storage = self.component_factory.create_watermark_storage(self.config)
            if self.watermark_storage:
                self.logger.info(f"✅ Watermark storage inicializado: {type(self.watermark_storage).__name__}")
            else:
                self.logger.warning("⚠️  Watermark storage configurado como necesario pero no se encontró configuración")
        else:
            self.logger.debug("ℹ️  Watermark storage no necesario para esta estrategia")
    
    def _strategy_needs_watermark_storage(self) -> bool:
        """Determina si la estrategia necesita watermark storage"""
        load_type = self.table_config.load_type.lower().strip() if self.table_config.load_type else 'full'
        
        incremental_types = ['incremental']
        
        if load_type in incremental_types:
            has_partition_column = (
                hasattr(self.table_config, 'partition_column') and 
                self.table_config.partition_column and 
                self.table_config.partition_column.strip()
            )
            return has_partition_column
        
        return False
    
    def _initialize_loader(self):
        """Inicializa el loader"""
        self.logger.info(f"📤 Creando loader ({self.config.loader_type})...")
        self.loader = self.component_factory.create_loader(self.config)
        self.logger.info(f"✅ Loader inicializado: {self.config.loader_type} -> {self.config.formatter_type}")
    
    def _initialize_monitor(self, monitor: Optional[IMonitor] = None, process_guid: Optional[str] = None):
        """Inicializa el monitor"""
        if monitor:
            self.monitor = monitor
            self.logger.debug("✅ Monitor proporcionado externamente")
        elif self.config.monitoring:
            self.monitor = self.component_factory.create_monitor(self.config, process_guid)
            if self.monitor:
                self.logger.info(f"✅ Monitor inicializado: {self.config.monitoring.provider}")
            else:
                self.logger.debug("ℹ️  Monitor no disponible")
        else:
            self.logger.debug("ℹ️  Monitor no configurado")
    
    def _initialize_strategy(self):
        """Inicializa la estrategia"""
        self.logger.info("🎯 Creando estrategia de extracción...")
        self.strategy = self.component_factory.create_strategy(
            config=self.config,
            table_config=self.table_config,
            watermark_storage=self.watermark_storage
        )
        self.logger.info(f"✅ Estrategia creada: {self.strategy.get_strategy_name()}")
    
    def _build_table_config(self, table_row):
        """Build TableConfig from CSV row (igual que extraction_orchestrator)""" 
        from ...extract_data.models import TableConfig
        
        # Apply load type logic - default to 'full' if not explicitly set
        load_type = table_row.get('LOAD_TYPE', '').strip()
        
        if not load_type:
            load_type = 'full'
        
        self.logger.debug(f"Table config - load_type: '{load_type}'")
        
        return TableConfig(
            stage_table_name=table_row.get('STAGE_TABLE_NAME', ''),
            source_schema=table_row.get('SOURCE_SCHEMA', ''),
            source_table=table_row.get('SOURCE_TABLE', ''),
            columns=self._process_columns_field(table_row.get('COLUMNS', '')),
            load_type=load_type,
            source_table_type=table_row.get('SOURCE_TABLE_TYPE', ''),
            partition_mode=table_row.get('PARTITION_MODE', 'AUTO'),
            partition_format=table_row.get('PARTITION_FORMAT') or 'year={YYYY}/month={MM}/day={DD}/hour={HH}',
            id_column=table_row.get('ID_COLUMN'),
            partition_column=table_row.get('PARTITION_COLUMN'),
            filter_exp=table_row.get('FILTER_EXP'),
            filter_column=table_row.get('FILTER_COLUMN'),
            filter_data_type=table_row.get('FILTER_DATA_TYPE'),
            join_expr=table_row.get('JOIN_EXPR'),
            delay_incremental_ini=table_row.get('DELAY_INCREMENTAL_INI'),
            delay_incremental_end=table_row.get('DELAY_INCREMENTAL_END') or '0',
            start_value=table_row.get('START_VALUE') or None,
            end_value=table_row.get('END_VALUE') or None
        )
    
    def _process_columns_field(self, columns_str: str) -> list:
        """Process COLUMNS field from CSV (igual que extraction_orchestrator)"""
        if not columns_str or not columns_str.strip():
            return []
        
        # Split by comma and strip whitespace
        columns = [col.strip() for col in columns_str.split(',') if col.strip()]
        return columns

