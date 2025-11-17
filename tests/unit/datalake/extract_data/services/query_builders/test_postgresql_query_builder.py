"""
Tests unitarios para PostgreSQLQueryBuilder.

Verifica que el QueryBuilder de PostgreSQL genera queries con sintaxis correcta:
- TIMESTAMP para fechas
- LIMIT/OFFSET para paginación
- Comillas dobles para identificadores
"""
import pytest
from aje_libs.datalake.shared.models import TableConfig, ExtractionParams
from aje_libs.datalake.extract_data.services.query_builders.postgresql_query_builder import PostgreSQLQueryBuilder


@pytest.mark.unit
class TestPostgreSQLQueryBuilder:
    """Tests para PostgreSQLQueryBuilder"""
    
    @pytest.fixture
    def table_config(self):
        """Fixture con configuración de tabla básica"""
        return TableConfig(
            stage_table_name="m_compania",
            source_table="mcompa1f",
            source_schema="public",
            columns="compania, nombre, direccion",
            load_type="full"
        )
    
    @pytest.fixture
    def query_builder(self, table_config):
        """Fixture que crea un PostgreSQLQueryBuilder"""
        return PostgreSQLQueryBuilder(table_config)
    
    def test_build_select_query_basic(self, query_builder):
        """Test que valida query SELECT básico para PostgreSQL"""
        params = ExtractionParams(
            table_name="public.mcompa1f",
            columns=["compania", "nombre", "direccion"]
        )
        
        query = query_builder.build_select_query(params)
        
        assert "SELECT" in query.upper()
        assert "FROM public.mcompa1f" in query
        assert "compania" in query
        assert "nombre" in query
        assert "direccion" in query
    
    def test_build_select_query_with_where(self, query_builder):
        """Test que valida query SELECT con WHERE"""
        params = ExtractionParams(
            table_name="public.mcompa1f",
            columns=["compania", "nombre"],
            where_conditions=["compania > '001'"]
        )
        
        query = query_builder.build_select_query(params)
        
        assert "WHERE" in query.upper()
        assert "compania > '001'" in query
    
    def test_build_select_query_with_limit(self, query_builder):
        """Test que valida query SELECT con LIMIT (PostgreSQL)"""
        params = ExtractionParams(
            table_name="public.mcompa1f",
            columns=["compania"],
            limit=100
        )
        
        query = query_builder.build_select_query(params)
        
        # PostgreSQL usa LIMIT
        assert "LIMIT 100" in query.upper()
    
    def test_build_select_query_with_order_by_and_limit(self, query_builder):
        """Test que valida query SELECT con ORDER BY y LIMIT"""
        params = ExtractionParams(
            table_name="public.mcompa1f",
            columns=["compania"],
            order_by="compania",
            limit=100
        )
        
        query = query_builder.build_select_query(params)
        
        assert "ORDER BY compania" in query.upper()
        assert "LIMIT 100" in query.upper()
    
    def test_format_datetime_value(self, query_builder):
        """Test que valida formateo de valores datetime para PostgreSQL"""
        formatted = query_builder.format_datetime_value("2025-01-15 10:30:00.123456", precision=6)
        
        assert "TIMESTAMP(6)" in formatted.upper()
        assert "2025-01-15 10:30:00.123456" in formatted
        assert "::" in formatted  # PostgreSQL usa :: para casting
    
    def test_format_datetime_comparison(self, query_builder):
        """Test que valida comparación datetime con casting para PostgreSQL"""
        comparison = query_builder.format_datetime_comparison(
            column="fecultmod",
            value="2025-01-15 10:30:00.123456",
            operator=">"
        )
        
        assert "fecultmod::TIMESTAMP(6)" in comparison
        assert ">" in comparison
        assert "::TIMESTAMP(6)" in comparison
    
    def test_build_pagination_clause_limit(self, query_builder):
        """Test que valida cláusula de paginación con LIMIT"""
        clause = query_builder.build_pagination_clause(limit=100)
        
        assert "LIMIT 100" in clause.upper()
    
    def test_build_pagination_clause_limit_offset(self, query_builder):
        """Test que valida cláusula de paginación con LIMIT/OFFSET"""
        clause = query_builder.build_pagination_clause(limit=100, offset=50)
        
        assert "LIMIT 100" in clause.upper()
        assert "OFFSET 50" in clause.upper()
    
    def test_build_chunked_query(self, query_builder):
        """Test que valida query paginado para chunking"""
        base_query = "SELECT compania FROM public.mcompa1f"
        chunked = query_builder.build_chunked_query(
            base_query=base_query,
            order_by="compania",
            offset=0,
            chunk_size=1000
        )
        
        assert "ORDER BY compania" in chunked.upper()
        assert "LIMIT 1000" in chunked.upper()
        assert "OFFSET 0" in chunked.upper()
    
    def test_quote_identifier(self, query_builder):
        """Test que valida comillas de identificadores (comillas dobles para PostgreSQL)"""
        quoted = query_builder.quote_identifier("mi_tabla")
        
        assert quoted == '"mi_tabla"'
    
    def test_quote_identifier_already_quoted(self, query_builder):
        """Test que valida que no duplica comillas si ya están"""
        quoted = query_builder.quote_identifier('"mi_tabla"')
        
        assert quoted == '"mi_tabla"'
    
    def test_quote_identifier_from_brackets(self, query_builder):
        """Test que convierte brackets a comillas dobles"""
        quoted = query_builder.quote_identifier("[mi_tabla]")
        
        assert quoted == '"mi_tabla"'
    
    def test_build_min_max_query(self, query_builder):
        """Test que valida query MIN/MAX para PostgreSQL"""
        query = query_builder.build_min_max_query(
            column="compania",
            additional_where="compania > '001'"
        )
        
        assert "SELECT MIN(compania) as min_val" in query.upper()
        assert "MAX(compania) as max_val" in query.upper()
        assert "FROM" in query.upper()
        assert "WHERE" in query.upper()
        assert "compania <> 0" in query
        assert "compania > '001'" in query


@pytest.mark.unit
class TestPostgreSQLQueryBuilderWithJoins:
    """Tests para PostgreSQLQueryBuilder con JOINs"""
    
    @pytest.fixture
    def table_config_with_join(self):
        """Fixture con configuración de tabla con JOIN"""
        return TableConfig(
            stage_table_name="m_compania",
            source_table="mcompa1f m",
            source_schema="public",
            columns="m.compania, m.nombre, t.monsol",
            load_type="full",
            join_expr="inner join public.mparam1f t on t.compania = m.compania"
        )
    
    @pytest.fixture
    def query_builder(self, table_config_with_join):
        """Fixture que crea un PostgreSQLQueryBuilder con JOIN"""
        return PostgreSQLQueryBuilder(table_config_with_join)
    
    def test_build_min_max_query_with_join(self, query_builder):
        """Test que valida query MIN/MAX con JOIN"""
        query = query_builder.build_min_max_query(column="m.compania")
        
        assert "MIN(m.compania)" in query
        assert "MAX(m.compania)" in query
        assert "inner join" in query.lower()
        assert "mparam1f" in query

