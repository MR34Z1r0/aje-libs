"""
Tests de importación para verificar que todos los módulos críticos se pueden importar.

Estos tests detectan errores de importación temprano, antes de que se ejecute
cualquier lógica de negocio. Son especialmente útiles para detectar:
- Imports incorrectos (ej: '...shared' en lugar de '....shared')
- Módulos faltantes
- Dependencias circulares
- Errores de sintaxis en módulos importados
"""
import pytest


class TestCriticalImports:
    """Tests para verificar que los módulos críticos se pueden importar."""

    def test_extract_data_orchestrator_imports(self):
        """Verifica que DataExtractionOrchestrator se puede importar."""
        from aje_libs.datalake.extract_data.orchestrators.extraction_orchestrator import (
            DataExtractionOrchestrator,
        )
        assert DataExtractionOrchestrator is not None

    def test_sql_server_extractor_imports(self):
        """
        Verifica que SQLServerExtractor se puede importar.
        
        Este test detecta el error que tuvimos:
        ModuleNotFoundError: No module named 'aje_libs.datalake.extract_data.shared'
        """
        from aje_libs.datalake.extract_data.services.extractors.sql_server_extractor import (
            SQLServerExtractor,
        )
        assert SQLServerExtractor is not None

    def test_s3_loader_imports(self):
        """Verifica que S3Loader se puede importar."""
        from aje_libs.datalake.extract_data.services.loaders.s3_loader import (
            S3Loader,
        )
        assert S3Loader is not None

    def test_shared_config_imports(self):
        """Verifica que get_settings se puede importar desde shared.config."""
        from aje_libs.datalake.shared.config import get_settings
        assert get_settings is not None
        
        # Verificar que se puede llamar
        settings = get_settings()
        assert settings is not None

    def test_extractor_factory_imports(self):
        """Verifica que ExtractorFactory se puede importar."""
        from aje_libs.datalake.extract_data.factories.extractor_factory import (
            ExtractorFactory,
        )
        assert ExtractorFactory is not None

    def test_component_initializer_imports(self):
        """Verifica que ComponentInitializer se puede importar."""
        from aje_libs.datalake.extract_data.orchestrators.component_initializer import (
            ComponentInitializer,
        )
        assert ComponentInitializer is not None

    def test_light_transform_orchestrator_imports(self):
        """Verifica que LightTransformOrchestrator se puede importar."""
        pytest.importorskip("pyspark", reason="pyspark requerido para light_transform")
        from aje_libs.datalake.light_transform.orchestrators.light_transform_orchestrator import (
            LightTransformOrchestrator,
        )
        assert LightTransformOrchestrator is not None

    def test_all_shared_models_import(self):
        """Verifica que todos los modelos compartidos se pueden importar."""
        from aje_libs.datalake.shared.models import (
            DatabaseConfig,
            LoadMode,
            ResourceRef,
            TableConfig,
        )
        assert DatabaseConfig is not None
        assert LoadMode is not None
        assert ResourceRef is not None
        assert TableConfig is not None

    def test_all_shared_services_import(self):
        """Verifica que todos los servicios compartidos se pueden importar."""
        from aje_libs.datalake.shared.services.logging import LoggerService
        from aje_libs.datalake.shared.services.monitoring import MonitorService
        from aje_libs.datalake.shared.services.storage import S3StorageProvider
        
        assert LoggerService is not None
        assert MonitorService is not None
        assert S3StorageProvider is not None

    def test_all_factories_import(self):
        """Verifica que todas las factories se pueden importar."""
        from aje_libs.datalake.extract_data.factories.configuration_provider_factory import (
            ConfigurationProviderFactory,
        )
        from aje_libs.datalake.shared.factories import MonitorFactory
        
        assert ConfigurationProviderFactory is not None
        assert MonitorFactory is not None

