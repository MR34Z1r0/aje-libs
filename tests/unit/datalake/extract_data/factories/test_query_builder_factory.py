"""
Tests unitarios para QueryBuilderFactory.

Verifica que el factory crea el QueryBuilder apropiado según el tipo de base de datos.
"""
import pytest
from aje_libs.datalake.shared.models import TableConfig
from aje_libs.datalake.extract_data.factories.query_builder_factory import QueryBuilderFactory
from aje_libs.datalake.extract_data.services.query_builders.sql_server_query_builder import SQLServerQueryBuilder
from aje_libs.datalake.extract_data.services.query_builders.postgresql_query_builder import PostgreSQLQueryBuilder


@pytest.mark.unit
class TestQueryBuilderFactory:
    """Tests para QueryBuilderFactory"""
    
    @pytest.fixture
    def table_config(self):
        """Fixture con configuración de tabla básica"""
        return TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="mcompa1f",
            source_schema="dbo",
            columns="compania, nombre",
            load_type="full"
        )
    
    def test_create_sqlserver_query_builder(self, table_config):
        """Test que valida creación de SQLServerQueryBuilder"""
        builder = QueryBuilderFactory.create(
            db_type="sqlserver",
            table_config=table_config
        )
        
        assert isinstance(builder, SQLServerQueryBuilder)
        assert builder.table_config == table_config
    
    def test_create_sqlserver_query_builder_with_mssql_alias(self, table_config):
        """Test que valida que 'mssql' también crea SQLServerQueryBuilder"""
        builder = QueryBuilderFactory.create(
            db_type="mssql",
            table_config=table_config
        )
        
        assert isinstance(builder, SQLServerQueryBuilder)
    
    def test_create_postgresql_query_builder(self, table_config):
        """Test que valida creación de PostgreSQLQueryBuilder"""
        builder = QueryBuilderFactory.create(
            db_type="postgresql",
            table_config=table_config
        )
        
        assert isinstance(builder, PostgreSQLQueryBuilder)
        assert builder.table_config == table_config
    
    def test_create_postgresql_query_builder_with_postgres_alias(self, table_config):
        """Test que valida que 'postgres' también crea PostgreSQLQueryBuilder"""
        builder = QueryBuilderFactory.create(
            db_type="postgres",
            table_config=table_config
        )
        
        assert isinstance(builder, PostgreSQLQueryBuilder)
    
    def test_create_with_unsupported_db_type(self, table_config):
        """Test que valida error con tipo de DB no soportado"""
        with pytest.raises(ValueError) as exc_info:
            QueryBuilderFactory.create(
                db_type="mysql",
                table_config=table_config
            )
        
        assert "no está soportado" in str(exc_info.value).lower()
        assert "mysql" in str(exc_info.value).lower()
    
    def test_get_supported_db_types(self):
        """Test que valida lista de tipos de DB soportados"""
        supported = QueryBuilderFactory.get_supported_db_types()
        
        assert "sqlserver" in supported
        assert "mssql" in supported
        assert "postgresql" in supported
        assert "postgres" in supported
        assert len(supported) >= 4
    
    def test_register_builder(self, table_config):
        """Test que valida registro de nuevo QueryBuilder"""
        from aje_libs.datalake.extract_data.contracts.query_builder_interface import IQueryBuilder
        
        # Crear un mock builder
        class MockQueryBuilder(IQueryBuilder):
            def build_select_query(self, params):
                return "SELECT * FROM test"
            def build_min_max_query(self, column, additional_where=None):
                return f"SELECT MIN({column}), MAX({column}) FROM test"
            def format_datetime_value(self, value, precision=6):
                return f"'{value}'"
            def format_datetime_comparison(self, column, value, operator=">"):
                return f"{column} {operator} '{value}'"
            def build_pagination_clause(self, limit, offset=None):
                return f"LIMIT {limit}"
            def build_chunked_query(self, base_query, order_by, offset, chunk_size):
                return f"{base_query} LIMIT {chunk_size} OFFSET {offset}"
            def quote_identifier(self, identifier):
                return f"`{identifier}`"
        
        # Registrar el nuevo builder
        QueryBuilderFactory.register_builder("mysql", MockQueryBuilder)
        
        # Verificar que se puede crear
        builder = QueryBuilderFactory.create(
            db_type="mysql",
            table_config=table_config
        )
        
        assert isinstance(builder, MockQueryBuilder)
        
        # Limpiar: remover el registro (opcional, para no afectar otros tests)
        # En producción, esto se haría de forma más controlada

