from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest

from aje_libs.datalake.extract_data.models.extraction_config import ExtractionConfig
from aje_libs.datalake.extract_data.models.extraction_result import ExtractionResult
from aje_libs.datalake.extract_data.orchestrators.extraction_orchestrator import (
    DataExtractionOrchestrator,
)
from aje_libs.datalake.shared.models import LoadMode, TableConfig, DatabaseConfig


class FakeMonitor:
    def __init__(self) -> None:
        self.start_calls: List[Dict[str, Any]] = []
        self.success_calls: List[Dict[str, Any]] = []
        self.error_calls: List[Dict[str, Any]] = []

    def log_start(self, table_name: str, job_name: str, metadata: Dict[str, Any]) -> None:
        self.start_calls.append(
            {"table_name": table_name, "job_name": job_name, "metadata": metadata}
        )

    def log_success(self, table_name: str, job_name: str, metadata: Dict[str, Any]) -> None:
        self.success_calls.append(
            {"table_name": table_name, "job_name": job_name, "metadata": metadata}
        )

    def log_error(self, table_name: str, error_message: str, job_name: str, metadata: Dict[str, Any]) -> None:
        self.error_calls.append(
            {
                "table_name": table_name,
                "error_message": error_message,
                "job_name": job_name,
                "metadata": metadata,
            }
        )


class FakeStrategy:
    def get_strategy_name(self) -> str:
        return "fake_strategy"

    def validate_config(self) -> bool:
        return True

    def generate_queries(self) -> List[Dict[str, Any]]:
        # No se usarán en este smoke test porque parchearemos _execute_extraction_strategy
        return []


@pytest.mark.integration
def test_extraction_orchestrator_execute_happy_path(monkeypatch):
    """
    Smoke/integration test del flujo principal de execute():
    - Inicializa componentes (parcheando _initialize_components).
    - Ejecuta la estrategia (parcheando _execute_extraction_strategy).
    - Llama a log_start y log_success del monitor.
    """

    # 1. Config mínima
    extraction_config = ExtractionConfig(
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        table_name="my_table",
        max_threads=2,
        chunk_size=1000,
        load_mode=LoadMode.NORMAL,
    )

    fake_monitor = FakeMonitor()
    orchestrator = DataExtractionOrchestrator(
        extraction_config=extraction_config,
        monitor=fake_monitor,
        process_guid="test-guid",
    )

    # 2. Parchear _initialize_components para inyectar dependencias mínimas
    def fake_initialize_components(self) -> None:  # type: ignore[override]
        self.monitor = fake_monitor
        self.strategy = FakeStrategy()
        self.table_config = TableConfig(
            stage_table_name="stg_my_table",
            source_schema="dbo",
            source_table="my_table",
            load_type="full",
            columns="id,col1",
        )
        self.database_config = DatabaseConfig(
            endpoint_name="endpoint",
            db_type="sqlserver",
            server="srv",
            database="db",
            username="user",
            secret_key="pwd",
            secret_name="secret",
            port=1433,
        )

    monkeypatch.setattr(
        DataExtractionOrchestrator,
        "_initialize_components",
        fake_initialize_components,
    )

    # 3. Parchear _execute_extraction_strategy para devolver un ExtractionResult simple
    def fake_execute_extraction_strategy(self) -> ExtractionResult:  # type: ignore[override]
        now = datetime.now()
        return ExtractionResult(
            success=True,
            table_name=self.extraction_config.table_name,
            records_extracted=10,
            files_created=["s3://bucket/path/file1.parquet"],
            execution_time_seconds=1.23,
            strategy_used=self.strategy.get_strategy_name(),
            metadata={"test": "ok"},
            start_time=now,
            end_time=now,
            files_metadata=[
                {"file_size_mb": 1.5},
            ],
        )

    monkeypatch.setattr(
        DataExtractionOrchestrator,
        "_execute_extraction_strategy",
        fake_execute_extraction_strategy,
    )

    # 4. Ejecutar
    result = orchestrator.execute()

    # 5. Asserts sobre el resultado
    assert result.success is True
    assert result.table_name == "my_table"
    assert result.records_extracted == 10
    assert result.files_created == ["s3://bucket/path/file1.parquet"]
    assert result.strategy_used == "fake_strategy"

    # 6. Verificar que el monitor fue llamado con información coherente
    assert len(fake_monitor.start_calls) == 1
    start_call = fake_monitor.start_calls[0]
    assert start_call["table_name"] == "my_table"
    assert start_call["job_name"] == "fake_strategy"

    assert len(fake_monitor.success_calls) == 1
    success_call = fake_monitor.success_calls[0]
    assert success_call["table_name"] == "my_table"
    assert success_call["job_name"].startswith("extract_fake_strategy")
    assert success_call["metadata"]["records_extracted"] == 10


@pytest.mark.integration
def test_extraction_orchestrator_component_initialization(monkeypatch):
    """
    Test que verifica que los componentes se pueden inicializar correctamente.
    
    Este test es más realista que el anterior porque:
    - NO mockea completamente _initialize_components
    - Permite que ComponentInitializer se ejecute realmente
    - Solo mockea las dependencias externas (AWS, BD, etc.)
    
    Esto detecta errores de importación en los extractors, loaders, etc.
    """
    from aje_libs.datalake.extract_data.orchestrators.component_initializer import (
        ComponentInitializer,
    )
    from aje_libs.datalake.extract_data.factories.configuration_provider_factory import (
        ConfigurationProviderFactory,
    )
    
    # 1. Config mínima
    extraction_config = ExtractionConfig(
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        table_name="my_table",
        max_threads=2,
        chunk_size=1000,
        load_mode=LoadMode.NORMAL,
    )
    
    fake_monitor = FakeMonitor()
    
    # 2. Mock del configuration_provider para evitar cargar CSVs reales
    fake_config_provider = Mock()
    fake_config_provider.get_table_config.return_value = TableConfig(
        stage_table_name="stg_my_table",
        source_schema="dbo",
        source_table="my_table",
        load_type="full",
        columns="id,col1",
    )
    fake_config_provider.get_database_config.return_value = DatabaseConfig(
        endpoint_name="endpoint",
        db_type="sqlserver",
        server="srv",
        database="db",
        username="user",
        secret_key="pwd",
        secret_name="secret",
        port=1433,
    )
    
    # 3. Mock de SecretProviderFactory para evitar llamadas reales a AWS
    fake_secret_provider = Mock()
    fake_secret_provider.get_secret.return_value = "fake_password"
    
    def fake_create_secret_provider(*args, **kwargs):
        return fake_secret_provider
    
    # Parchear en el módulo donde se importa SecretProviderFactory
    monkeypatch.setattr(
        "aje_libs.datalake.shared.factories.secret_provider_factory.SecretProviderFactory.create",
        fake_create_secret_provider
    )
    
    # 4. Crear ComponentInitializer y ejecutar initialize_all
    # ✅ ESTO EJECUTA EL CÓDIGO REAL DE INICIALIZACIÓN
    # Si hay errores de importación (como el que tuvimos), este test fallará
    initializer = ComponentInitializer(
        extraction_config=extraction_config,
        configuration_provider=fake_config_provider,
        monitor=fake_monitor,
        process_guid="test-guid",
    )
    
    # ✅ ESTA LLAMADA INSTANCIA REALMENTE SQLServerExtractor
    # Detecta errores de importación inmediatamente
    components = initializer.initialize_all(
        configuration_provider=fake_config_provider,
        monitor=fake_monitor,
        process_guid="test-guid",
    )
    
    # Verificar que se inicializaron los componentes
    assert components is not None
    assert hasattr(components, 'extractor') or 'extractor' in components
    assert hasattr(components, 'loader') or 'loader' in components
    assert hasattr(components, 'formatter') or 'formatter' in components


