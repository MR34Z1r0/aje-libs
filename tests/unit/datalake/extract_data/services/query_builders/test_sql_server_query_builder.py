"""
Tests unitarios para SQLServerQueryBuilder.

Verifica que el QueryBuilder de SQL Server genera queries con sintaxis correcta:
- DATETIME2 para fechas
- TOP u OFFSET/FETCH para paginación
- Brackets para identificadores
"""
import pytest
from aje_libs.datalake.shared.models import TableConfig, ExtractionParams
from aje_libs.datalake.extract_data.services.query_builders.sql_server_query_builder import SQLServerQueryBuilder


@pytest.mark.unit
class TestSQLServerQueryBuilder:
    """Tests para SQLServerQueryBuilder"""
    
    @pytest.fixture
    def table_config(self):
        """Fixture con configuración de tabla básica"""
        return TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="mcompa1f",
            source_schema="dbo",
            columns="compania, nombre, direccion",
            load_type="full"
        )
    
    @pytest.fixture
    def query_builder(self, table_config):
        """Fixture que crea un SQLServerQueryBuilder"""
        return SQLServerQueryBuilder(table_config)
    
    def test_build_select_query_basic(self, query_builder):
        """Test que valida query SELECT básico para SQL Server"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania", "nombre", "direccion"]
        )
        
        query = query_builder.build_select_query(params)
        
        assert "SELECT" in query.upper()
        assert "FROM dbo.mcompa1f" in query
        assert "compania" in query
        assert "nombre" in query
        assert "direccion" in query
    
    def test_build_select_query_with_where(self, query_builder):
        """Test que valida query SELECT con WHERE"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania", "nombre"],
            where_conditions=["compania > '001'"]
        )
        
        query = query_builder.build_select_query(params)
        
        assert "WHERE" in query.upper()
        assert "compania > '001'" in query
    
    def test_build_select_query_with_top(self, query_builder):
        """Test que valida query SELECT con TOP (SQL Server sin ORDER BY)"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            limit=100
        )
        
        query = query_builder.build_select_query(params)
        
        # SQL Server usa TOP cuando no hay ORDER BY
        assert "TOP 100" in query.upper()
        assert "SELECT TOP 100" in query.upper()
    
    def test_build_select_query_with_offset_fetch(self, query_builder):
        """Test que valida query SELECT con OFFSET/FETCH (SQL Server con ORDER BY)"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            order_by="compania",
            limit=100
        )
        
        query = query_builder.build_select_query(params)
        
        # SQL Server usa OFFSET/FETCH cuando hay ORDER BY
        assert "ORDER BY compania" in query.upper()
        assert "OFFSET" in query.upper()
        assert "FETCH NEXT 100 ROWS ONLY" in query.upper()
    
    def test_format_datetime_value(self, query_builder):
        """Test que valida formateo de valores datetime para SQL Server"""
        formatted = query_builder.format_datetime_value("2025-01-15 10:30:00.123456", precision=6)
        
        assert "CAST" in formatted.upper()
        assert "DATETIME2(6)" in formatted.upper()
        assert "2025-01-15 10:30:00.123456" in formatted
    
    def test_format_datetime_comparison(self, query_builder):
        """Test que valida comparación datetime con casting"""
        comparison = query_builder.format_datetime_comparison(
            column="fecultmod",
            value="2025-01-15 10:30:00.123456",
            operator=">"
        )
        
        assert "CAST(fecultmod AS DATETIME2(6))" in comparison
        assert ">" in comparison
        assert "DATETIME2(6)" in comparison
    
    def test_build_pagination_clause_top(self, query_builder):
        """Test que valida cláusula de paginación con TOP"""
        clause = query_builder.build_pagination_clause(limit=100)
        
        assert "TOP 100" in clause.upper()
    
    def test_build_pagination_clause_offset_fetch(self, query_builder):
        """Test que valida cláusula de paginación con OFFSET/FETCH"""
        clause = query_builder.build_pagination_clause(limit=100, offset=50)
        
        assert "OFFSET 50 ROWS" in clause.upper()
        assert "FETCH NEXT 100 ROWS ONLY" in clause.upper()
    
    def test_build_chunked_query(self, query_builder):
        """Test que valida query paginado para chunking"""
        base_query = "SELECT compania FROM dbo.mcompa1f"
        chunked = query_builder.build_chunked_query(
            base_query=base_query,
            order_by="compania",
            offset=0,
            chunk_size=1000
        )
        
        assert "ORDER BY compania" in chunked.upper()
        assert "OFFSET 0 ROWS" in chunked.upper()
        assert "FETCH NEXT 1000 ROWS ONLY" in chunked.upper()
    
    def test_quote_identifier(self, query_builder):
        """Test que valida comillas de identificadores (brackets para SQL Server)"""
        quoted = query_builder.quote_identifier("mi_tabla")
        
        assert quoted == "[mi_tabla]"
    
    def test_quote_identifier_already_quoted(self, query_builder):
        """Test que valida que no duplica comillas si ya están"""
        quoted = query_builder.quote_identifier("[mi_tabla]")
        
        assert quoted == "[mi_tabla]"
    
    def test_build_min_max_query(self, query_builder):
        """Test que valida query MIN/MAX para SQL Server"""
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
class TestSQLServerQueryBuilderWithJoins:
    """Tests para SQLServerQueryBuilder con JOINs"""
    
    @pytest.fixture
    def table_config_with_join(self):
        """Fixture con configuración de tabla con JOIN"""
        return TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="mcompa1f m",
            source_schema="dbo",
            columns="m.compania, m.nombre, t.monsol",
            load_type="full",
            join_expr="inner join dbo.mparam1f(nolock) t on t.compania = m.compania"
        )
    
    @pytest.fixture
    def query_builder(self, table_config_with_join):
        """Fixture que crea un SQLServerQueryBuilder con JOIN"""
        return SQLServerQueryBuilder(table_config_with_join)
    
    def test_build_min_max_query_with_join(self, query_builder):
        """Test que valida query MIN/MAX con JOIN"""
        query = query_builder.build_min_max_query(column="m.compania")
        
        assert "MIN(m.compania)" in query
        assert "MAX(m.compania)" in query
        assert "inner join" in query.lower()
        assert "mparam1f" in query

