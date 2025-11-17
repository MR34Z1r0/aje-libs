import pytest

from aje_libs.datalake.shared.builders.database_config_builder import DatabaseConfigBuilder


@pytest.mark.unit
def test_database_config_builder_fluent_interface_builds_config():
    builder = (
        DatabaseConfigBuilder.create()
        .with_endpoint_name("my-endpoint")
        .with_db_type("SQLSERVER")
        .with_server("srv")
        .with_database("db")
        .with_username("user")
        .with_secrets(secret_name="my-secret", secret_key="pwd")
        .with_port(1433)
    )

    cfg = builder.build()

    assert cfg.endpoint_name == "my-endpoint"
    assert cfg.db_type == "sqlserver"
    assert cfg.server == "srv"
    assert cfg.database == "db"
    assert cfg.username == "user"
    assert cfg.secret_name == "my-secret"
    assert cfg.secret_key == "pwd"
    assert cfg.port == 1433


@pytest.mark.unit
def test_database_config_builder_from_dict_maps_typical_csv_fields():
    data = {
        "ENDPOINT_NAME": "ep",
        "BD_TYPE": "postgres",
        "SRC_SERVER_NAME": "host",
        "SRC_DB_NAME": "db",
        "SRC_DB_USERNAME": "user",
        "SRC_DB_SECRET": "secret-key",
        "DB_PORT_NUMBER": "5432",
    }

    cfg = DatabaseConfigBuilder.create().from_dict(data).build()

    assert cfg.endpoint_name == "ep"
    assert cfg.db_type == "postgres"
    assert cfg.server == "host"
    assert cfg.database == "db"
    assert cfg.username == "user"
    assert cfg.secret_key == "secret-key"
    assert cfg.secret_name != ""  # debe haberse seteado algún nombre de secreto
    assert cfg.port == 5432


@pytest.mark.unit
def test_database_config_builder_missing_required_fields_raises():
    builder = DatabaseConfigBuilder.create().with_endpoint_name("ep")

    with pytest.raises(ValueError):
        builder.build()


@pytest.mark.unit
def test_database_config_builder_requires_secret_name_when_secret_key_present():
    builder = (
        DatabaseConfigBuilder.create()
        .with_endpoint_name("ep")
        .with_db_type("sqlserver")
        .with_server("srv")
        .with_database("db")
        .with_username("user")
    )
    # Inyectamos secret_key manualmente sin secret_name para disparar la validación
    builder._config["secret_key"] = "pwd"  # type: ignore[attr-defined]

    with pytest.raises(ValueError):
        builder.build()


