"""
Tests unitarios para ParquetTableWriter.

Estos tests verifican que:
1. ParquetTableWriter se puede inicializar correctamente
2. Los métodos overwrite, append, merge, write_time_range y cleanup funcionan
3. Las operaciones de merge y time_range se implementan correctamente sin Delta/Iceberg

Nota: Estos tests requieren pyspark. Si no está instalado, se saltan automáticamente.
"""
import pytest

# Saltar tests si pyspark no está disponible
pyspark = pytest.importorskip("pyspark", reason="pyspark requerido para tests de ParquetTableWriter")

from unittest.mock import Mock, MagicMock, patch
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from aje_libs.datalake.light_transform.services.storage.parquet.parquet_table_writer import (
    ParquetTableWriter,
)


@pytest.fixture(scope="module")
def spark_session():
    """Crea una SparkSession para los tests"""
    spark = SparkSession.builder \
        .appName("test_parquet_writer") \
        .master("local[1]") \
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
        .getOrCreate()
    yield spark
    spark.stop()


@pytest.fixture
def sample_df(spark_session):
    """Crea un DataFrame de ejemplo para los tests"""
    schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("name", StringType(), True),
        StructField("value", IntegerType(), True),
    ])
    data = [(1, "Alice", 100), (2, "Bob", 200), (3, "Charlie", 300)]
    return spark_session.createDataFrame(data, schema)


@pytest.fixture
def parquet_writer(spark_session):
    """Crea una instancia de ParquetTableWriter para los tests"""
    logger = Mock()
    return ParquetTableWriter(spark=spark_session, logger=logger)


class TestParquetTableWriterInitialization:
    """Tests para verificar que ParquetTableWriter se inicializa correctamente."""

    def test_writer_can_be_initialized(self, spark_session):
        """Test que verifica que ParquetTableWriter se puede inicializar."""
        writer = ParquetTableWriter(spark=spark_session)
        assert writer is not None
        assert writer.spark == spark_session
        assert writer.logger is not None

    def test_writer_can_be_initialized_with_logger(self, spark_session):
        """Test que verifica que ParquetTableWriter acepta un logger personalizado."""
        custom_logger = Mock()
        writer = ParquetTableWriter(spark=spark_session, logger=custom_logger)
        assert writer.logger == custom_logger


class TestParquetTableWriterOverwrite:
    """Tests para el método overwrite."""

    def test_overwrite_writes_data(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que overwrite escribe datos correctamente."""
        test_path = str(tmp_path / "test_overwrite")
        
        # Escribir datos
        parquet_writer.overwrite(sample_df, test_path)
        
        # Verificar que se escribieron
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3
        assert written_df.columns == ["id", "name", "value"]

    def test_overwrite_with_partitions(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que overwrite respeta columnas de partición."""
        test_path = str(tmp_path / "test_overwrite_partitioned")
        
        # Escribir con partición
        parquet_writer.overwrite(sample_df, test_path, partition_cols=["id"])
        
        # Verificar que se escribieron
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3


class TestParquetTableWriterAppend:
    """Tests para el método append."""

    def test_append_adds_data(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que append agrega datos sin sobrescribir."""
        test_path = str(tmp_path / "test_append")
        
        # Escribir datos iniciales
        parquet_writer.overwrite(sample_df, test_path)
        
        # Agregar más datos
        new_data = [(4, "David", 400), (5, "Eve", 500)]
        new_df = parquet_writer.spark.createDataFrame(new_data, sample_df.schema)
        parquet_writer.append(new_df, test_path)
        
        # Verificar que se agregaron
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 5  # 3 originales + 2 nuevos


class TestParquetTableWriterMerge:
    """Tests para el método merge."""

    def test_merge_creates_table_if_not_exists(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que merge crea la tabla si no existe."""
        test_path = str(tmp_path / "test_merge_new")
        
        # Hacer merge en tabla que no existe
        parquet_writer.merge(
            sample_df,
            test_path,
            merge_condition="old.id = new.id"
        )
        
        # Verificar que se creó
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3

    def test_merge_updates_existing_records(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que merge actualiza registros existentes."""
        test_path = str(tmp_path / "test_merge_update")
        
        # Escribir datos iniciales
        parquet_writer.overwrite(sample_df, test_path)
        
        # Crear datos actualizados (mismo id, diferentes valores)
        updated_data = [(1, "Alice Updated", 150), (2, "Bob Updated", 250)]
        updated_df = parquet_writer.spark.createDataFrame(updated_data, sample_df.schema)
        
        # Hacer merge
        parquet_writer.merge(
            updated_df,
            test_path,
            merge_condition="old.id = new.id"
        )
        
        # Verificar que se actualizaron
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3  # Mismo número de registros
        
        # Verificar que los valores se actualizaron
        alice = written_df.filter("id = 1").collect()[0]
        assert alice["name"] == "Alice Updated"
        assert alice["value"] == 150

    def test_merge_inserts_new_records(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que merge inserta nuevos registros."""
        test_path = str(tmp_path / "test_merge_insert")
        
        # Escribir datos iniciales
        parquet_writer.overwrite(sample_df, test_path)
        
        # Crear datos nuevos (ids diferentes)
        new_data = [(4, "David", 400), (5, "Eve", 500)]
        new_df = parquet_writer.spark.createDataFrame(new_data, sample_df.schema)
        
        # Hacer merge
        parquet_writer.merge(
            new_df,
            test_path,
            merge_condition="old.id = new.id"
        )
        
        # Verificar que se insertaron
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 5  # 3 originales + 2 nuevos

    def test_merge_handles_mixed_updates_and_inserts(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que merge maneja updates e inserts simultáneos."""
        test_path = str(tmp_path / "test_merge_mixed")
        
        # Escribir datos iniciales
        parquet_writer.overwrite(sample_df, test_path)
        
        # Crear datos mixtos (algunos updates, algunos inserts)
        mixed_data = [
            (1, "Alice Updated", 150),  # Update
            (4, "David", 400),          # Insert
            (2, "Bob Updated", 250),    # Update
            (5, "Eve", 500)             # Insert
        ]
        mixed_df = parquet_writer.spark.createDataFrame(mixed_data, sample_df.schema)
        
        # Hacer merge
        parquet_writer.merge(
            mixed_df,
            test_path,
            merge_condition="old.id = new.id"
        )
        
        # Verificar resultado
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 5  # 3 originales - 2 actualizados + 2 nuevos = 5 total
        
        # Verificar que los updates funcionaron
        alice = written_df.filter("id = 1").collect()[0]
        assert alice["name"] == "Alice Updated"
        
        # Verificar que los inserts funcionaron
        david = written_df.filter("id = 4").collect()[0]
        assert david["name"] == "David"


class TestParquetTableWriterTimeRange:
    """Tests para el método write_time_range."""

    def test_write_time_range_creates_table_if_not_exists(self, parquet_writer, tmp_path):
        """Test que verifica que write_time_range crea la tabla si no existe."""
        test_path = str(tmp_path / "test_time_range_new")
        
        # Crear DataFrame con columna de período
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("period", StringType(), True),
            StructField("value", IntegerType(), True),
        ])
        data = [("2024-01", 100), ("2024-02", 200), ("2024-03", 300)]
        df = parquet_writer.spark.createDataFrame(
            [(i, p, v) for i, (p, v) in enumerate(data, 1)],
            schema
        )
        
        # Hacer write_time_range
        time_range_config = {
            "period_column": "period",
            "period_values": ["2024-01"]
        }
        parquet_writer.write_time_range(df, test_path, time_range_config=time_range_config)
        
        # Verificar que se creó
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3

    def test_write_time_range_deletes_period_and_writes_new(self, parquet_writer, tmp_path):
        """Test que verifica que write_time_range elimina el período y escribe nuevos datos."""
        test_path = str(tmp_path / "test_time_range_delete")
        
        # Crear DataFrame inicial con columna de período
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("period", StringType(), True),
            StructField("value", IntegerType(), True),
        ])
        initial_data = [
            (1, "2024-01", 100),
            (2, "2024-02", 200),
            (3, "2024-03", 300),
        ]
        initial_df = parquet_writer.spark.createDataFrame(initial_data, schema)
        
        # Escribir datos iniciales
        parquet_writer.overwrite(initial_df, test_path)
        
        # Crear nuevos datos para el período 2024-01
        new_data = [
            (1, "2024-01", 150),  # Mismo período, valor actualizado
            (4, "2024-01", 400),   # Nuevo registro en el mismo período
        ]
        new_df = parquet_writer.spark.createDataFrame(new_data, schema)
        
        # Hacer write_time_range para eliminar 2024-01 y escribir nuevos
        time_range_config = {
            "period_column": "period",
            "period_values": ["2024-01"]
        }
        parquet_writer.write_time_range(new_df, test_path, time_range_config=time_range_config)
        
        # Verificar resultado
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        # Debería tener: 2 registros de 2024-01 (nuevos) + 2 registros de otros períodos (2024-02, 2024-03)
        assert written_df.count() == 4
        
        # Verificar que el período 2024-01 tiene los nuevos valores
        period_2024_01 = written_df.filter("period = '2024-01'").collect()
        assert len(period_2024_01) == 2
        values = [row["value"] for row in period_2024_01]
        assert 150 in values
        assert 400 in values


class TestParquetTableWriterCleanup:
    """Tests para el método cleanup."""

    def test_cleanup_removes_existing_data(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que cleanup elimina datos existentes."""
        test_path = str(tmp_path / "test_cleanup")
        
        # Escribir datos
        parquet_writer.overwrite(sample_df, test_path)
        
        # Verificar que existen
        written_df = parquet_writer.spark.read.format("parquet").load(test_path)
        assert written_df.count() == 3
        
        # Limpiar
        parquet_writer.cleanup(test_path)
        
        # Verificar que se eliminaron (debería fallar al leer)
        with pytest.raises(Exception):  # Puede ser AnalysisException u otra excepción
            parquet_writer.spark.read.format("parquet").load(test_path).count()

    def test_cleanup_handles_nonexistent_path(self, parquet_writer, tmp_path):
        """Test que verifica que cleanup maneja rutas que no existen."""
        test_path = str(tmp_path / "test_cleanup_nonexistent")
        
        # Limpiar ruta que no existe (no debería fallar)
        parquet_writer.cleanup(test_path)
        
        # Verificar que el logger registró el mensaje apropiado
        assert any("no encontrada" in str(call) or "nada que eliminar" in str(call) 
                   for call in parquet_writer.logger.info.call_args_list)


class TestParquetTableWriterErrorHandling:
    """Tests para manejo de errores."""

    def test_merge_raises_error_on_invalid_condition(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que merge lanza error con condición inválida."""
        test_path = str(tmp_path / "test_merge_invalid")
        
        with pytest.raises(ValueError, match="Condición de merge inválida"):
            parquet_writer.merge(
                sample_df,
                test_path,
                merge_condition="invalid condition"
            )

    def test_write_time_range_raises_error_without_config(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que write_time_range lanza error sin time_range_config."""
        test_path = str(tmp_path / "test_time_range_no_config")
        
        with pytest.raises(ValueError, match="time_range_config es requerido"):
            parquet_writer.write_time_range(sample_df, test_path)

    def test_write_time_range_raises_error_without_period_column(self, parquet_writer, sample_df, tmp_path):
        """Test que verifica que write_time_range lanza error sin period_column."""
        test_path = str(tmp_path / "test_time_range_no_period")
        
        time_range_config = {
            "period_values": ["2024-01"]
            # Falta period_column
        }
        
        with pytest.raises(ValueError, match="period_column es requerido"):
            parquet_writer.write_time_range(
                sample_df,
                test_path,
                time_range_config=time_range_config
            )

