import pytest

from aje_libs.datalake.shared.factories.monitor_factory import MonitorFactory
from aje_libs.datalake.shared.services.monitoring import MonitorService
from aje_libs.datalake.shared.exceptions import ConfigurationException


class DummyEventLogger:
    pass


class DummyNotificationService:
    pass


class DummyLogger:
    def __init__(self):
        self.debugs = []

    def debug(self, msg: str, *args, **kwargs):
        self.debugs.append(msg)


@pytest.mark.unit
def test_monitor_factory_creates_default_dynamodb_monitor_with_builders(monkeypatch):
    dummy_logger = DummyLogger()

    # Evitar builders reales; devolvemos objetos simples
    def fake_build_event_logger(event_logger_type, logger=None, **config):
        assert event_logger_type == "default"
        return DummyEventLogger()

    def fake_build_notification_service(notification_provider, sns_topic_arn, sns_topic_arns, logger=None, **config):  # noqa: E501
        assert notification_provider == "sns"
        return DummyNotificationService()

    monkeypatch.setattr(
        "aje_libs.datalake.shared.factories.monitor_factory.EventLoggerBuilder.build",
        staticmethod(fake_build_event_logger),
    )
    monkeypatch.setattr(
        "aje_libs.datalake.shared.factories.monitor_factory.NotificationServiceBuilder.build",
        staticmethod(fake_build_notification_service),
    )

    monitor = MonitorFactory.create(
        monitor_type="dynamodb",
        logger=dummy_logger,
        table_name="logs_table",
        project_name="proj",
        team="team",
        data_source="ds",
        endpoint_name="endpoint",
        environment="dev",
        sns_topic_arn="arn:aws:sns:region:acct:topic",
        region="us-east-1",
    )

    assert isinstance(monitor, MonitorService)
    # Aseguramos que el monitor tenga las dependencias inyectadas
    assert isinstance(monitor.event_logger, DummyEventLogger)
    assert isinstance(monitor.notification_service, DummyNotificationService)


@pytest.mark.unit
def test_monitor_factory_register_and_get_supported_types_and_invalid_type():
    class CustomMonitor(MonitorService):
        pass

    MonitorFactory.register_monitor("custom", CustomMonitor)

    supported = MonitorFactory.get_supported_types()
    assert "custom" in supported

    # Crear con tipo custom usando dependencias ya construidas
    monitor = MonitorFactory.create(
        monitor_type="custom",
        event_logger=DummyEventLogger(),
        notification_service=DummyNotificationService(),
        logger=None,
    )
    assert isinstance(monitor, CustomMonitor)

    # Tipo inválido debe lanzar ConfigurationException
    with pytest.raises(ConfigurationException):
        MonitorFactory.create("invalid_type")


