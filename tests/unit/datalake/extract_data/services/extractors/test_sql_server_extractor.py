"""
Tests unitarios para SQLServerExtractor.

Estos tests verifican que:
1. El extractor se puede inicializar correctamente (detecta errores de importación)
2. Los imports están correctos
3. La configuración se carga correctamente
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from aje_libs.datalake.shared.models import DatabaseConfig
from aje_libs.datalake.extract_data.services.extractors.sql_server_extractor import (
    SQLServerExtractor,
)


class TestSQLServerExtractorInitialization:
    """Tests para verificar que SQLServerExtractor se inicializa correctamente."""

    def test_extractor_can_be_initialized_with_valid_config(self, monkeypatch):
        """
        Test que verifica que SQLServerExtractor se puede inicializar.
        
        Este test detecta errores de importación (como el que tuvimos con
        'aje_libs.datalake.extract_data.shared' que debería ser 'aje_libs.datalake.shared').
        """
        # Mock del secret provider para evitar llamadas reales a AWS
        fake_secret_provider = Mock()
        fake_secret_provider.get_secret.return_value = "fake_password"
        
        # Mock de SecretProviderFactory para que no intente crear un provider real
        def fake_create_secret_provider(*args, **kwargs):
            return fake_secret_provider
        
        # Parchear en el módulo donde se importa SecretProviderFactory
        monkeypatch.setattr(
            "aje_libs.datalake.shared.factories.secret_provider_factory.SecretProviderFactory.create",
            fake_create_secret_provider
        )
        
        # Config válida
        db_config = DatabaseConfig(
            endpoint_name="test-endpoint",
            db_type="sqlserver",
            server="test-server.database.windows.net",
            database="testdb",
            username="testuser",
            secret_key="password",
            secret_name="test/secret/password",
            port=1433,
        )
        
        # ✅ ESTE TEST FALLA SI HAY ERRORES DE IMPORTACIÓN
        # Si el import está mal (ej: '...shared' en lugar de '....shared'),
        # este test fallará inmediatamente
        extractor = SQLServerExtractor(
            config=db_config,
            secret_provider=fake_secret_provider,
            name_logger="test.extractor"
        )
        
        # Verificar que se inicializó correctamente
        assert extractor.config == db_config
        assert extractor._secret_provider == fake_secret_provider
        assert extractor.max_retries is not None
        assert extractor.retry_delay is not None
        assert extractor.use_sqlalchemy is True
        assert extractor.logger is not None

    def test_extractor_creates_secret_provider_if_not_provided(self, monkeypatch):
        """
        Test que verifica que SQLServerExtractor crea un secret provider
        automáticamente si no se proporciona uno.
        """
        # Mock de SecretProviderFactory
        fake_secret_provider = Mock()
        fake_secret_provider.get_secret.return_value = "fake_password"
        
        created_provider = None
        
        def fake_create_secret_provider(*args, **kwargs):
            nonlocal created_provider
            created_provider = fake_secret_provider
            return fake_secret_provider
        
        # Parchear en el módulo donde se importa SecretProviderFactory
        monkeypatch.setattr(
            "aje_libs.datalake.shared.factories.secret_provider_factory.SecretProviderFactory.create",
            fake_create_secret_provider
        )
        
        db_config = DatabaseConfig(
            endpoint_name="test-endpoint",
            db_type="sqlserver",
            server="test-server.database.windows.net",
            database="testdb",
            username="testuser",
            secret_key="password",
            secret_name="test/secret/password",
            port=1433,
        )
        
        # No proporcionar secret_provider
        extractor = SQLServerExtractor(
            config=db_config,
            secret_provider=None,
            name_logger="test.extractor"
        )
        
        # Verificar que se creó un secret provider
        assert extractor._secret_provider is not None
        assert created_provider is not None

    def test_extractor_loads_settings_correctly(self, monkeypatch):
        """
        Test que verifica que el extractor carga la configuración centralizada
        correctamente (get_settings).
        
        Este test verifica que get_settings se puede importar y llamar sin errores.
        Los valores específicos dependen de la configuración real, pero lo importante
        es que no haya errores de importación.
        """
        # Mock del secret provider
        fake_secret_provider = Mock()
        fake_secret_provider.get_secret.return_value = "fake_password"
        
        # Parchear en el módulo donde se importa SecretProviderFactory
        monkeypatch.setattr(
            "aje_libs.datalake.shared.factories.secret_provider_factory.SecretProviderFactory.create",
            lambda *args, **kwargs: fake_secret_provider
        )
        
        db_config = DatabaseConfig(
            endpoint_name="test-endpoint",
            db_type="sqlserver",
            server="test-server.database.windows.net",
            database="testdb",
            username="testuser",
            secret_key="password",
            secret_name="test/secret/password",
            port=1433,
        )
        
        # ✅ ESTE TEST FALLA SI HAY ERRORES DE IMPORTACIÓN EN get_settings
        # Si el import está mal, este test fallará inmediatamente
        extractor = SQLServerExtractor(
            config=db_config,
            secret_provider=fake_secret_provider,
        )
        
        # Verificar que se cargaron los settings (valores por defecto o reales)
        assert extractor.max_retries is not None
        assert extractor.retry_delay is not None
        assert isinstance(extractor.max_retries, int)
        assert isinstance(extractor.retry_delay, (int, float))

