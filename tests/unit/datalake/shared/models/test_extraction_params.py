"""
Tests unitarios para ExtractionParams.

Valida que el modelo de parámetros de extracción funciona correctamente
y que está ubicado en shared/models para evitar dependencias circulares.
"""
import pytest
from aje_libs.datalake.shared.models import ExtractionParams


@pytest.mark.unit
class TestExtractionParams:
    """Tests para ExtractionParams"""
    
    def test_extraction_params_creation_basic(self):
        """Test que valida creación básica de ExtractionParams"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f m",
            columns=["m.compania", "m.nombre"]
        )
        
        assert params.table_name == "dbo.mcompa1f m"
        assert params.columns == ["m.compania", "m.nombre"]
        assert params.where_conditions == []
        assert params.order_by is None
        assert params.limit is None
    
    def test_extraction_params_with_where_conditions(self):
        """Test que valida ExtractionParams con condiciones WHERE"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania", "nombre"],
            where_conditions=["compania > '001'", "estado = 'A'"]
        )
        
        assert len(params.where_conditions) == 2
        assert "compania > '001'" in params.where_conditions
        assert "estado = 'A'" in params.where_conditions
    
    def test_extraction_params_add_where_condition(self):
        """Test que valida agregar condiciones WHERE dinámicamente"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"]
        )
        
        params.add_where_condition("compania > '001'")
        params.add_where_condition("estado = 'A'")
        
        assert len(params.where_conditions) == 2
        assert "compania > '001'" in params.where_conditions
    
    def test_extraction_params_get_where_clause(self):
        """Test que valida construcción de cláusula WHERE"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            where_conditions=["compania > '001'", "estado = 'A'"]
        )
        
        where_clause = params.get_where_clause()
        assert where_clause == "compania > '001' AND estado = 'A'"
    
    def test_extraction_params_get_where_clause_empty(self):
        """Test que valida get_where_clause retorna None cuando no hay condiciones"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"]
        )
        
        where_clause = params.get_where_clause()
        assert where_clause is None
    
    def test_extraction_params_get_columns_string(self):
        """Test que valida get_columns_string con lista de columnas"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania", "nombre", "direccion"]
        )
        
        columns_str = params.get_columns_string()
        assert columns_str == "compania, nombre, direccion"
    
    def test_extraction_params_get_columns_string_wildcard(self):
        """Test que valida get_columns_string con wildcard"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["*"]
        )
        
        columns_str = params.get_columns_string()
        assert columns_str == "*"
    
    def test_extraction_params_get_columns_string_empty(self):
        """Test que valida get_columns_string con lista vacía (default a *)"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=[]
        )
        
        # Después de __post_init__, columns vacío se convierte a ['*']
        assert params.columns == ["*"]
        columns_str = params.get_columns_string()
        assert columns_str == "*"
    
    def test_extraction_params_with_metadata(self):
        """Test que valida ExtractionParams con metadatos"""
        metadata = {
            "needs_partitioning": True,
            "partition_column": "fecultmod",
            "chunk_size": 1000000
        }
        
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            metadata=metadata
        )
        
        assert params.metadata["needs_partitioning"] is True
        assert params.metadata["partition_column"] == "fecultmod"
        assert params.metadata["chunk_size"] == 1000000
    
    def test_extraction_params_with_chunking(self):
        """Test que valida ExtractionParams con configuración de chunking"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            chunk_size=1000000,
            chunk_column="compania"
        )
        
        assert params.chunk_size == 1000000
        assert params.chunk_column == "compania"
    
    def test_extraction_params_with_pagination(self):
        """Test que valida ExtractionParams con paginación"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            order_by="compania",
            limit=1000
        )
        
        assert params.order_by == "compania"
        assert params.limit == 1000
    
    def test_extraction_params_validation_table_name_required(self):
        """Test que valida que table_name es requerido"""
        with pytest.raises(ValueError, match="table_name es requerido"):
            ExtractionParams(
                table_name="",
                columns=["compania"]
            )
    
    def test_extraction_params_empty_where_conditions_filtered(self):
        """Test que valida que condiciones WHERE vacías se filtran"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"],
            where_conditions=["compania > '001'", "", "  ", "estado = 'A'"]
        )
        
        # Condiciones vacías se filtran en __post_init__
        assert len(params.where_conditions) == 2
        assert "compania > '001'" in params.where_conditions
        assert "estado = 'A'" in params.where_conditions
    
    def test_extraction_params_add_where_condition_strips_whitespace(self):
        """Test que valida que add_where_condition hace strip de whitespace"""
        params = ExtractionParams(
            table_name="dbo.mcompa1f",
            columns=["compania"]
        )
        
        params.add_where_condition("  compania > '001'  ")
        params.add_where_condition("")
        params.add_where_condition("  ")
        
        # Solo la condición válida se agrega
        assert len(params.where_conditions) == 1
        assert params.where_conditions[0] == "compania > '001'"


@pytest.mark.unit
class TestExtractionParamsLocation:
    """Tests para validar que ExtractionParams está en shared/models"""
    
    def test_extraction_params_import_from_shared_models(self):
        """Test que valida que ExtractionParams se importa desde shared.models"""
        from aje_libs.datalake.shared.models import ExtractionParams
        
        # Verificar que está en el módulo correcto
        assert ExtractionParams.__module__ == "aje_libs.datalake.shared.models.extraction_params"
    
    def test_extraction_params_no_circular_dependency(self):
        """Test que valida que no hay dependencia circular con strategies"""
        # Este test verifica que podemos importar ExtractionParams
        # sin importar strategies (evitando dependencia circular)
        from aje_libs.datalake.shared.models import ExtractionParams
        
        # Crear instancia sin problemas
        params = ExtractionParams(
            table_name="test_table",
            columns=["col1", "col2"]
        )
        
        assert params is not None
        assert params.table_name == "test_table"

