"""
Tests unitarios para QueryBuilder.

Estos tests verifican que:
1. Los queries se generan correctamente para diferentes tipos de tablas
2. Los queries incluyen correctamente las columnas, schemas, joins y filtros
3. Los queries funcionan con las tablas M_COMPANIA, T_DOCUMENTO_VENTA_DETALLE y M_SUCURSAL
"""
import pytest

from aje_libs.datalake.shared.models import TableConfig
from aje_libs.datalake.extract_data.services.query_builder import QueryBuilder


@pytest.mark.unit
class TestQueryBuilderStandardQuery:
    """Tests para verificar que QueryBuilder genera queries estándar correctamente."""

    def test_build_standard_query_m_compania(self):
        """Test que valida el query generado para M_COMPANIA con el query exacto esperado."""
        # Configuración basada en el query real de producción
        # Nota: El FROM en el query esperado es "mcompa1f m" sin schema
        table_config = TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="mcompa1f m",  # Tabla con alias (sin schema en FROM)
            source_schema=None,  # Sin schema para que el FROM sea solo "mcompa1f m"
            columns=(
                "dbo.func_cas_todatetime(m.fecultmod, m.horultimod) lastmodifydate, "
                "m.compania, "
                "replace(replace(m.nombre, char(13), ''), char(10), '') nombre, "
                "cast(cast(m.persona as int) as varchar(20)) persona, "
                "m.tipovia, "
                "replace(replace(m.direccion, char(13), ''), char(10), '') direccion, "
                "rtrim(ltrim(m.pais)) pais, "
                "m.departamen, m.provincia, m.zonapostal, "
                "m.telefono1, m.telefono2, m.telefono3, m.telefono4, "
                "m.fax, m.flgtipocia, m.ruc, m.nota, m.regigv, m.estado, "
                "m.feccrea, m.horcrea, m.usucrea, "
                "m.fecultmod, m.horultimod, m.ultusumod, m.abrevbco, "
                "case when m.aprobreq = 0x46 then 'F' when m.aprobreq = 0x54 then 'T' end aprobreq, "
                "case when m.aproboco = 0x46 then 'F' when m.aproboco = 0x54 then 'T' end aproboco, "
                "m.ipenlace, "
                "case when m.flgctrfaoc = 0x46 then 'F' when m.flgctrfaoc = 0x54 then 'T' end flgctrfaoc, "
                "case when m.flgrestart = 0x46 then 'F' when m.flgrestart = 0x54 then 'T' end flgrestart, "
                "case when m.flgaprogj = 0x46 then 'F' when m.flgaprogj = 0x54 then 'T' end flgaprogj, "
                "cast(cast(m.cantemple as int) as varchar(20)) cantemple, "
                "m.sucprin, m.coidioma, m.intercom, m.flgbi, "
                "t.monsol"
            ),
            load_type="full",
            id_column="rtrim(ltrim(m.compania))",
            join_expr="inner join dbo.mparam1f(nolock) t on t.compania = m.compania",
            filter_exp="m.compania in (select compania from dbo.mcompa1f b where b.flgbi = 'a')"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Query esperado exacto
        expected_query = (
            "SELECT rtrim(ltrim(m.compania)) as id, "
            "dbo.func_cas_todatetime(m.fecultmod, m.horultimod) lastmodifydate, "
            "m.compania, "
            "replace(replace(m.nombre, char(13), ''), char(10), '') nombre, "
            "cast(cast(m.persona as int) as varchar(20)) persona, "
            "m.tipovia, "
            "replace(replace(m.direccion, char(13), ''), char(10), '') direccion, "
            "rtrim(ltrim(m.pais)) pais, "
            "m.departamen, m.provincia, m.zonapostal, "
            "m.telefono1, m.telefono2, m.telefono3, m.telefono4, "
            "m.fax, m.flgtipocia, m.ruc, m.nota, m.regigv, m.estado, "
            "m.feccrea, m.horcrea, m.usucrea, "
            "m.fecultmod, m.horultimod, m.ultusumod, m.abrevbco, "
            "case when m.aprobreq = 0x46 then 'F' when m.aprobreq = 0x54 then 'T' end aprobreq, "
            "case when m.aproboco = 0x46 then 'F' when m.aproboco = 0x54 then 'T' end aproboco, "
            "m.ipenlace, "
            "case when m.flgctrfaoc = 0x46 then 'F' when m.flgctrfaoc = 0x54 then 'T' end flgctrfaoc, "
            "case when m.flgrestart = 0x46 then 'F' when m.flgrestart = 0x54 then 'T' end flgrestart, "
            "case when m.flgaprogj = 0x46 then 'F' when m.flgaprogj = 0x54 then 'T' end flgaprogj, "
            "cast(cast(m.cantemple as int) as varchar(20)) cantemple, "
            "m.sucprin, m.coidioma, m.intercom, m.flgbi, "
            "t.monsol "
            "FROM mcompa1f m "
            "inner join dbo.mparam1f(nolock) t on t.compania = m.compania "
            "WHERE (m.compania in (select compania from dbo.mcompa1f b where b.flgbi = 'a'))"
        )
        
        # Normalizar ambos queries para comparación (eliminar espacios extra)
        def normalize_query(q):
            # Reemplazar múltiples espacios con uno solo
            import re
            q = re.sub(r'\s+', ' ', q.strip())
            # Normalizar mayúsculas/minúsculas para palabras clave SQL
            q = re.sub(r'\bSELECT\b', 'SELECT', q, flags=re.IGNORECASE)
            q = re.sub(r'\bFROM\b', 'FROM', q, flags=re.IGNORECASE)
            q = re.sub(r'\bWHERE\b', 'WHERE', q, flags=re.IGNORECASE)
            q = re.sub(r'\bINNER JOIN\b', 'inner join', q, flags=re.IGNORECASE)
            return q.strip()
        
        normalized_query = normalize_query(query)
        normalized_expected = normalize_query(expected_query)
        
        # Validar que el query generado coincide exactamente con el esperado
        assert normalized_query == normalized_expected, (
            f"Query generado no coincide con el esperado.\n"
            f"Esperado:\n{normalized_expected}\n\n"
            f"Generado:\n{normalized_query}"
        )
        
        # Validaciones adicionales de componentes clave
        assert "rtrim(ltrim(m.compania)) as id" in query or "rtrim(ltrim(m.compania)) AS id" in query
        assert "FROM" in query.upper()
        assert "mcompa1f m" in query
        assert "inner join" in query.lower()
        assert "mparam1f" in query
        assert "WHERE" in query.upper()
        assert "m.compania in (select compania from dbo.mcompa1f b where b.flgbi = 'a')" in query

    def test_build_standard_query_t_documento_venta_detalle(self):
        """Test que valida el query generado para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="id_documento_venta_detalle, id_compania, id_sucursal, id_documento_venta, cod_articulo, cant_unidad, imp_cobrar",
            load_type="full",
            id_column="id_documento_venta_detalle"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar estructura básica del query
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "T_DOCUMENTO_VENTA_DETALLE" in query
        
        # Validar que incluye las columnas principales
        assert "id_documento_venta_detalle" in query
        assert "id_compania" in query
        assert "id_sucursal" in query
        assert "cod_articulo" in query
        
        # Validar que incluye id_column como id
        assert "id_documento_venta_detalle as id" in query or "id_documento_venta_detalle AS id" in query

    def test_build_standard_query_m_sucursal(self):
        """Test que valida el query generado para M_SUCURSAL."""
        table_config = TableConfig(
            stage_table_name="M_SUCURSAL",
            source_table="M_SUCURSAL",
            source_schema="dbo",
            columns="id_sucursal, cod_sucursal, nombre_sucursal, id_compania, estado",
            load_type="full"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar estructura básica del query
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "M_SUCURSAL" in query
        
        # Validar que incluye las columnas
        assert "id_sucursal" in query
        assert "cod_sucursal" in query
        assert "id_compania" in query

    def test_build_standard_query_t_documento_venta(self):
        """Test que valida el query generado para T_DOCUMENTO_VENTA."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA",
            source_table="T_DOCUMENTO_VENTA",
            source_schema="dbo",
            columns=(
                "id_documento_venta, id_compania, id_sucursal, id_almacen, "
                "id_tipo_documento, cod_documento_venta, nro_documento_venta, "
                "fecha_emision, fecha_liquidacion, cod_cliente, cod_vendedor, "
                "cod_moneda, tipo_cambio_mn, tipo_cambio_me, estado"
            ),
            load_type="full",
            id_column="id_documento_venta"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar estructura básica del query
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "T_DOCUMENTO_VENTA" in query
        
        # Validar que incluye las columnas principales
        assert "id_documento_venta" in query
        assert "id_compania" in query
        assert "id_sucursal" in query
        assert "cod_documento_venta" in query
        assert "fecha_emision" in query
        
        # Validar que incluye id_column como id
        assert "id_documento_venta as id" in query or "id_documento_venta AS id" in query

    def test_build_standard_query_with_filter(self):
        """Test que valida el query generado con filtro para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="id_documento_venta_detalle, id_compania, id_sucursal",
            load_type="full",
            filter_exp="estado = 'ACTIVO'"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar que incluye WHERE con el filtro
        assert "WHERE" in query.upper()
        assert "estado" in query
        assert "ACTIVO" in query

    def test_build_standard_query_with_join(self):
        """Test que valida el query generado con JOIN para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="dvd.id_documento_venta_detalle, dvd.id_compania, dvd.id_sucursal, c.nombre_compania",
            load_type="full",
            join_expr="INNER JOIN dbo.M_COMPANIA c ON dvd.id_compania = c.id_compania"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar que incluye el JOIN
        assert "JOIN" in query.upper()
        assert "M_COMPANIA" in query
        assert "id_compania" in query

    def test_build_standard_query_with_additional_where(self):
        """Test que valida el query generado con WHERE adicional."""
        table_config = TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="M_COMPANIA",
            source_schema="dbo",
            columns="id_compania, cod_compania",
            load_type="full"
        )
        
        query_builder = QueryBuilder(table_config)
        additional_where = "id_compania > 100"
        query = query_builder.build_standard_query(additional_where=additional_where)
        
        # Validar que incluye el WHERE adicional
        assert "WHERE" in query.upper()
        assert "id_compania > 100" in query


@pytest.mark.unit
class TestQueryBuilderPartitionedQuery:
    """Tests para verificar que QueryBuilder genera queries particionados correctamente."""

    def test_build_partitioned_query_t_documento_venta_detalle(self):
        """Test que valida el query particionado para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="id_documento_venta_detalle, id_compania, id_sucursal",
            load_type="partitioned",
            partition_column="id_documento_venta_detalle"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_partitioned_query(
            partition_column="id_documento_venta_detalle",
            start_value=1000,
            end_value=2000
        )
        
        # Validar estructura del query particionado
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "WHERE" in query.upper()
        
        # Validar rango de partición
        assert "id_documento_venta_detalle >= 1000" in query
        assert "id_documento_venta_detalle < 2000" in query
        assert "AND" in query.upper()


@pytest.mark.unit
class TestQueryBuilderDateRangeQuery:
    """Tests para verificar que QueryBuilder genera queries con rango de fechas correctamente."""

    def test_build_date_range_query_t_documento_venta_detalle(self):
        """Test que valida el query con rango de fechas para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="id_documento_venta_detalle, id_compania, fecha_creacion",
            load_type="date_range",
            filter_column="fecha_creacion"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_date_range_query(
            start_date="2024-01-01",
            end_date="2024-12-31",
            date_column="fecha_creacion"
        )
        
        # Validar estructura del query con rango de fechas
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "WHERE" in query.upper()
        
        # Validar que incluye la columna de fecha
        assert "fecha_creacion" in query
        assert "BETWEEN" in query.upper()
        assert "IS NOT NULL" in query.upper()


@pytest.mark.unit
class TestQueryBuilderMinMaxQuery:
    """Tests para verificar que QueryBuilder genera queries MIN/MAX correctamente."""

    def test_build_min_max_query_m_compania(self):
        """Test que valida el query MIN/MAX para M_COMPANIA."""
        table_config = TableConfig(
            stage_table_name="M_COMPANIA",
            source_table="M_COMPANIA",
            source_schema="dbo",
            columns="id_compania",
            load_type="full"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_min_max_query(column="id_compania")
        
        # Validar estructura del query MIN/MAX
        assert "SELECT" in query.upper()
        assert "MIN(id_compania)" in query
        assert "MAX(id_compania)" in query
        assert "as min_val" in query.lower() or "AS min_val" in query
        assert "as max_val" in query.lower() or "AS max_val" in query
        assert "FROM" in query.upper()
        assert "WHERE" in query.upper()
        assert "id_compania <> 0" in query


@pytest.mark.unit
class TestQueryBuilderComplexScenarios:
    """Tests para escenarios complejos con múltiples tablas."""

    def test_query_with_join_between_tables(self):
        """Test que valida un query complejo con JOIN entre T_DOCUMENTO_VENTA_DETALLE, M_COMPANIA y M_SUCURSAL."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="dvd.id_documento_venta_detalle, dvd.id_compania, dvd.id_sucursal, c.nombre_compania, s.nombre_sucursal",
            load_type="full",
            join_expr=(
                "INNER JOIN dbo.M_COMPANIA c ON dvd.id_compania = c.id_compania "
                "INNER JOIN dbo.M_SUCURSAL s ON dvd.id_sucursal = s.id_sucursal"
            ),
            filter_exp="dvd.estado = 'ACTIVO'"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar estructura completa del query
        assert "SELECT" in query.upper()
        assert "FROM" in query.upper()
        assert "JOIN" in query.upper()
        
        # Validar que incluye todas las tablas
        assert "T_DOCUMENTO_VENTA_DETALLE" in query
        assert "M_COMPANIA" in query
        assert "M_SUCURSAL" in query
        
        # Validar que incluye las columnas
        assert "id_documento_venta_detalle" in query
        assert "nombre_compania" in query
        assert "nombre_sucursal" in query
        
        # Validar que incluye el filtro
        assert "WHERE" in query.upper()
        assert "estado" in query

    def test_query_with_id_column_and_filter(self):
        """Test que valida un query con id_column y filtro para T_DOCUMENTO_VENTA_DETALLE."""
        table_config = TableConfig(
            stage_table_name="T_DOCUMENTO_VENTA_DETALLE",
            source_table="T_DOCUMENTO_VENTA_DETALLE",
            source_schema="dbo",
            columns="id_compania, id_sucursal, cod_articulo, cant_unidad",
            load_type="incremental",
            id_column="id_documento_venta_detalle",
            filter_exp="id_compania IN (1, 2, 3)"
        )
        
        query_builder = QueryBuilder(table_config)
        query = query_builder.build_standard_query()
        
        # Validar que incluye id_column como id
        assert "id_documento_venta_detalle as id" in query.lower() or "id_documento_venta_detalle AS id" in query
        
        # Validar que incluye las otras columnas
        assert "id_compania" in query
        assert "cod_articulo" in query
        
        # Validar que incluye el filtro
        assert "WHERE" in query.upper()
        assert "id_compania IN" in query or "id_compania in" in query.lower()

