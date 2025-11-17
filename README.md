# aje-libs

[![PyPI version](https://badge.fury.io/py/aje-libs.svg)](https://badge.fury.io/py/aje-libs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/aje-libs)](https://pypi.org/project/aje-libs/)

Biblioteca de utilidades para proyectos de AWS en Ajegroup. Proporciona helpers, orquestadores y utilidades comunes para simplificar el desarrollo de aplicaciones en la nube.

## 📋 Tabla de Contenidos

- [Instalación](#instalación)
- [Módulos Principales](#módulos-principales)
  - [Common - Utilidades Comunes](#common---utilidades-comunes)
  - [Datalake - Procesamiento de Datos](#datalake---procesamiento-de-datos)
- [Ejemplos Prácticos](#ejemplos-prácticos)
- [Testing con pytest](#testing-con-pytest)
- [Contribución](#contribución)

## 🚀 Instalación

### Instalación en Producción

```bash
pip install aje-libs
```

### Instalación en Desarrollo

```bash
cd aje-libs/
pip install -e .
```

### Requisitos

- Python >= 3.9
- boto3 (para helpers de AWS)
- aws-lambda-powertools (opcional, para logging avanzado)

## 📦 Módulos Principales

### Common - Utilidades Comunes

El módulo `common` proporciona helpers y utilidades para trabajar con servicios de AWS y funcionalidades compartidas.

#### Helpers de AWS

##### S3Helper

Helper simplificado para operaciones con Amazon S3.

```python
from aje_libs.common import S3Helper

# Inicializar helper
s3_helper = S3Helper(bucket_name="mi-bucket", region_name="us-east-1")

# Subir archivo
s3_path = s3_helper.upload_file(
    file_path="/ruta/local/archivo.txt",
    object_key="carpeta/archivo.txt"
)

# Descargar archivo
s3_helper.download_file(
    object_key="carpeta/archivo.txt",
    file_path="/ruta/local/descarga.txt"
)

# Listar objetos con filtros
objects = s3_helper.list_objects_advanced(
    prefix="carpeta/",
    filters={
        'extension': 'txt',
        'min_size': 1024,
        'date_range': {
            'start': '2024-01-01',
            'end': '2024-12-31'
        }
    }
)

# Verificar existencia
if s3_helper.object_exists("carpeta/archivo.txt"):
    print("El archivo existe")

# Obtener URL pre-firmada
url = s3_helper.get_presigned_url(
    object_key="carpeta/archivo.txt",
    expiration=3600
)
```

##### DynamoDBHelper

Helper para operaciones CRUD con Amazon DynamoDB.

```python
from aje_libs.common import DynamoDBHelper
from boto3.dynamodb.conditions import Key, Attr

# Inicializar helper (tabla con PK y SK)
dynamo_helper = DynamoDBHelper(
    table_name="mi-tabla",
    pk_name="PK",
    sk_name="SK",
    region_name="us-east-1"
)

# Insertar item
dynamo_helper.put_item({
    "PK": "USER#123",
    "SK": "PROFILE#456",
    "nombre": "Juan",
    "email": "juan@example.com"
})

# Obtener item
item = dynamo_helper.get_item(
    partition_key="USER#123",
    sort_key="PROFILE#456"
)

# Actualizar item
dynamo_helper.update_item(
    partition_key="USER#123",
    sort_key="PROFILE#456",
    update_expression="SET email = :email",
    expression_attribute_values={":email": "nuevo@example.com"}
)

# Query con begins_with
items = dynamo_helper.query_items_by_begins_pk_sk(
    partition_key="USER#",
    sort_key_portion="PROFILE#",
    limit=50
)

# Query por índice secundario
items = dynamo_helper.query_by_index(
    index_name="email-index",
    key_condition_expression=Key("email").eq("juan@example.com")
)

# Batch operations
dynamo_helper.batch_write_items(
    put_items=[
        {"PK": "USER#1", "SK": "PROFILE#1", "nombre": "Usuario 1"},
        {"PK": "USER#2", "SK": "PROFILE#2", "nombre": "Usuario 2"}
    ]
)

# Scan con filtros
items = dynamo_helper.scan_table(
    filter_expression=Attr("activo").eq(True),
    limit=100
)
```

##### SecretsHelper

Helper para obtener secretos de AWS Secrets Manager.

```python
from aje_libs.common import SecretsHelper

# Inicializar helper
secrets_helper = SecretsHelper(secret_name="mi-secreto")

# Obtener valor completo del secreto
secret_data = secrets_helper.get_secret_value()
# Retorna: {"username": "admin", "password": "secret123"}

# Obtener valor específico por clave
password = secrets_helper.get_secret_value(key_name="password")
# Retorna: "secret123"
```

##### SSMParameterHelper

Helper para obtener parámetros de AWS Systems Manager Parameter Store.

```python
from aje_libs.common import SSMParameterHelper

# Inicializar helper
ssm_helper = SSMParameterHelper(parameter_name="/mi-app/config/database-url")

# Obtener parámetro (desencriptado automáticamente si es SecureString)
db_url = ssm_helper.get_parameter_value(with_decryption=True)
```

#### Logger

Sistema de logging configurable con soporte para AWS Lambda Powertools.

```python
from aje_libs.common import custom_logger, set_logger_config

# Configuración global (opcional)
set_logger_config(
    log_level=logging.INFO,
    log_file="/ruta/logs/app.log",
    service="mi-servicio",
    correlation_id="12345",
    owner="mi-equipo"
)

# Crear logger
logger = custom_logger(__name__)

# Usar logger
logger.info("Mensaje informativo")
logger.error("Mensaje de error")
logger.debug("Mensaje de debug")
logger.warning("Mensaje de advertencia")
```

#### BotoSessionManager

Gestor de sesiones de boto3 con soporte para múltiples regiones y perfiles.

```python
from aje_libs.common import BotoSessionManager

# Crear gestor
session_manager = BotoSessionManager(
    region_name="us-east-1",
    profile_name="mi-perfil"
)

# Obtener cliente
s3_client = session_manager.get_client("s3")
dynamodb_client = session_manager.get_client("dynamodb")
```

### Datalake - Procesamiento de Datos

El módulo `datalake` proporciona orquestadores y servicios para la extracción y transformación de datos.

#### 🏗️ Arquitectura del Módulo Datalake

El módulo `datalake.extract_data` está diseñado con una arquitectura desacoplada que separa las responsabilidades en tres capas principales:

```
┌─────────────────────────────────────────────────────────────┐
│                    ESTRATEGIA                                │
│              (FullLoadStrategy)                              │
│                                                              │
│  Responsabilidad:                                            │
│  • Decide QUÉ extraer (columnas, filtros)                    │
│  • Decide CÓMO extraer (full, incremental, particionado)   │
│  • Construye ExtractionParams (parámetros estructurados)    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 1. build_extraction_params()
                       │    Retorna: ExtractionParams
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              EXTRACTION PARAMS                              │
│         (shared/models/extraction_params.py)               │
│                                                              │
│  ✅ Ubicado en shared/models para evitar                    │
│     dependencias circulares (SOLID - DIP)                    │
│                                                              │
│  {                                                           │
│    table_name: "dbo.mcompa1f m",                            │
│    columns: ["m.compania", "m.nombre", ...],               │
│    where_conditions: ["m.compania > '001'"],                │
│    chunk_size: 1000000,                                     │
│    metadata: {...}                                          │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 2. build_select_query(params)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  QUERY BUILDER                               │
│            (SQLServerQueryBuilder)                           │
│                                                              │
│  Responsabilidad:                                            │
│  • Convierte ExtractionParams → SQL string                  │
│  • Aplica sintaxis específica del motor                     │
│  • Formatea valores (fechas, identificadores)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 3. Retorna: "SELECT TOP 1000 ..."
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTOR                                 │
│              (SQLServerExtractor)                            │
│                                                              │
│  Responsabilidad:                                            │
│  • Ejecuta el SQL string                                    │
│  • Obtiene datos de la base de datos                        │
│  • Retorna DataFrame con resultados                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 4. Retorna: DataFrame
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     LOADER                                   │
│                      (S3Loader)                              │
└─────────────────────────────────────────────────────────────┘
```

##### Componentes Principales

###### 1. **Strategies (Estrategias)** - Lógica de Negocio

Las estrategias definen **QUÉ** y **CÓMO** extraer datos, sin conocer detalles de la base de datos específica.

**Propósito:**
- Decidir qué datos extraer (columnas, tablas, filtros)
- Determinar cuándo extraer (full load, incremental, time range)
- Aplicar lógica de negocio (watermarks, particionado, chunking)
- Construir `ExtractionParams` estructurados

**Estrategias Disponibles:**
- `FullLoadStrategy`: Extrae toda la tabla (carga inicial, reset)
- `IncrementalStrategy`: Extrae solo datos nuevos usando watermarks
- `TimeRangeStrategy`: Extrae por rango de fechas específico

**Manejo Robusto de Configuración:**
- Las estrategias manejan correctamente `partition_mode=None` (normalizado desde 'NONE')
- Si `partition_mode` es `None`, usan 'AUTO' como valor por defecto
- Evitan errores de `AttributeError` cuando `partition_mode` es `None`

**Ejemplo:**
```python
from aje_libs.datalake.extract_data.strategies.implementations.full_load import FullLoadStrategy

strategy = FullLoadStrategy(table_config, extraction_config)
params = strategy.build_extraction_params()
# params contiene: table_name, columns, where_conditions, metadata, etc.
```

###### 2. **Query Builders** - Generación de SQL

Los Query Builders construyen el texto SQL específico para cada motor de base de datos.

**Propósito:**
- Convertir `ExtractionParams` → SQL string
- Aplicar sintaxis específica del motor (SQL Server, PostgreSQL, etc.)
- Formatear valores (fechas, identificadores, tipos de datos)
- Manejar particularidades (TOP vs LIMIT, DATETIME2 vs TIMESTAMP)

**Query Builders Disponibles:**
- `SQLServerQueryBuilder`: Para SQL Server
  - Usa `DATETIME2(6)` para fechas
  - Usa `TOP` o `OFFSET/FETCH` para paginación
  - Usa brackets `[identifier]` para identificadores
  
- `PostgreSQLQueryBuilder`: Para PostgreSQL
  - Usa `TIMESTAMP(6)` para fechas
  - Usa `LIMIT/OFFSET` para paginación
  - Usa comillas dobles `"identifier"` para identificadores

**Ejemplo:**
```python
from aje_libs.datalake.extract_data.factories.query_builder_factory import QueryBuilderFactory

# Crear QueryBuilder para SQL Server
query_builder = QueryBuilderFactory.create(
    db_type="sqlserver",
    table_config=table_config
)

# Construir query SQL
sql_query = query_builder.build_select_query(params)
# Resultado: "SELECT TOP 1000 m.compania FROM dbo.mcompa1f m WHERE ..."
```

**Ventajas:**
- ✅ Estrategias agnósticas a la base de datos
- ✅ Fácil agregar soporte para nuevos motores (MySQL, Oracle, etc.)
- ✅ Sintaxis SQL correcta para cada motor

###### 3. **Extractors** - Ejecución de SQL

Los Extractors ejecutan queries SQL y obtienen datos de la base de datos.

**Propósito:**
- Conectarse a la base de datos
- Ejecutar queries SQL
- Obtener resultados como DataFrames de pandas
- Manejar conexiones, pools, reintentos, chunking

**Extractors Disponibles:**
- `SQLServerExtractor`: Para SQL Server usando SQLAlchemy/pymssql

**Ejemplo:**
```python
from aje_libs.datalake.extract_data.services.extractors.sql_server_extractor import SQLServerExtractor

extractor = SQLServerExtractor(database_config)
extractor.connect()
df = extractor.execute_query(sql_query)
# df es un DataFrame de pandas con los datos
```

##### Comparación de Responsabilidades

| Componente | Responsabilidad | Conoce DB | Input | Output |
|------------|----------------|-----------|-------|--------|
| **Strategy** | Qué y cómo extraer (lógica de negocio) | ❌ No (agnóstico) | TableConfig, ExtractionConfig | ExtractionParams |
| **QueryBuilder** | Cómo construir SQL (sintaxis) | ✅ Sí (específico) | ExtractionParams | SQL string |
| **Extractor** | Cómo ejecutar SQL (conexión) | ✅ Sí (específico) | SQL string | DataFrame |

##### Flujo Completo de Ejecución

```python
# 1. ESTRATEGIA decide QUÉ y CÓMO
strategy = FullLoadStrategy(table_config, extraction_config)
params = strategy.build_extraction_params()

# 2. QUERY BUILDER convierte params → SQL
query_builder = QueryBuilderFactory.create("sqlserver", table_config)
sql_query = query_builder.build_select_query(params)

# 3. EXTRACTOR ejecuta SQL y obtiene datos
extractor = SQLServerExtractor(database_config)
extractor.connect()
df = extractor.execute_query(sql_query)

# 4. LOADER guarda datos
loader = S3Loader(config)
loader.save(df, destination_path)
```

##### 🏛️ Arquitectura y Principios SOLID

El módulo `extract_data` sigue principios SOLID para garantizar mantenibilidad y extensibilidad:

**Dependency Inversion Principle (DIP):**
- Las interfaces (`contracts/`) dependen de modelos compartidos (`shared/models/`)
- No dependen de implementaciones específicas (`strategies/`)
- `ExtractionParams` está en `shared/models/` para evitar dependencias circulares

**Single Responsibility Principle (SRP):**
- `ExtractionParams`: DTO puro para parámetros de extracción
- `TableConfig`: Modelo de configuración con validación y normalización
- Cada componente tiene una responsabilidad única y bien definida

**Normalización Automática:**
- `TableConfig` normaliza automáticamente valores como `partition_mode='NONE'` → `None`
- Maneja strings vacíos, variaciones de mayúsculas/minúsculas
- Las estrategias manejan correctamente valores `None` con defaults apropiados

**Ejemplo de Normalización:**
```python
from aje_libs.datalake.shared.models import TableConfig

# El CSV puede tener 'NONE', 'none', '', etc.
# TableConfig lo normaliza automáticamente
config = TableConfig(
    stage_table_name="mi_tabla",
    partition_mode="NONE"  # Se normaliza a None
)
assert config.partition_mode is None  # ✅ Normalizado

# Las estrategias manejan None correctamente
# Si partition_mode es None, usan 'AUTO' como default
```

##### Extensibilidad: Agregar Soporte para Nuevos Motores de Base de Datos

Para agregar soporte a un nuevo motor de base de datos (ej: MySQL, Oracle), solo necesitas:

1. **Crear el QueryBuilder** implementando `IQueryBuilder`:
```python
from aje_libs.datalake.extract_data.contracts.query_builder_interface import IQueryBuilder
from aje_libs.datalake.shared.models import ExtractionParams  # ✅ Modelo compartido

class MySQLQueryBuilder(IQueryBuilder):
    """QueryBuilder para MySQL"""
    
    def build_select_query(self, params: ExtractionParams) -> str:
        # Implementar construcción de SELECT para MySQL
        # MySQL usa LIMIT/OFFSET similar a PostgreSQL
        query = f"SELECT {', '.join(params.columns)} FROM {params.table_name}"
        if params.get_where_clause():
            query += f" WHERE {params.get_where_clause()}"
        if params.limit:
            query += f" LIMIT {params.limit}"
        return query
    
    def format_datetime_value(self, value: str, precision: int = 6) -> str:
        # MySQL usa DATETIME o TIMESTAMP
        return f"CAST('{value}' AS DATETIME)"
    
    # ... implementar otros métodos requeridos
```

2. **Registrarlo en el Factory**:
```python
from aje_libs.datalake.extract_data.factories.query_builder_factory import QueryBuilderFactory

QueryBuilderFactory.register_builder('mysql', MySQLQueryBuilder)
```

3. **¡Listo!** Las estrategias existentes funcionarán automáticamente con el nuevo motor:
```python
# El orquestador detectará automáticamente el tipo de DB y usará el QueryBuilder apropiado
orchestrator = DataExtractionOrchestrator(extraction_config)
result = orchestrator.execute()  # Funciona con MySQL sin cambios en las estrategias
```

**Ventajas de esta arquitectura:**
- ✅ No necesitas modificar las estrategias (full_load, incremental, time_range)
- ✅ No necesitas modificar el orquestador
- ✅ Solo creas el QueryBuilder específico para tu motor
- ✅ El código existente sigue funcionando sin cambios

#### DataExtractionOrchestrator

Orquestador principal para la extracción de datos desde bases de datos hacia almacenamiento en la nube.

El orquestador coordina todos los componentes (Strategies, QueryBuilders, Extractors, Loaders) de forma automática.

```python
from aje_libs.datalake.extract_data import DataExtractionOrchestrator
from aje_libs.datalake.extract_data.models import ExtractionConfig
from aje_libs.datalake.shared.models import LoadMode, TableConfig, DatabaseConfig

# Configurar base de datos
database_config = DatabaseConfig(
    host="servidor.database.com",
    port=1433,
    database="mi_base_datos",
    username="usuario",
    password="contraseña",
    db_type="sqlserver"
)

# Configurar tabla
table_config = TableConfig(
    table_name="mi_tabla",
    schema_name="dbo",
    primary_key="id"
)

# Configurar extracción
extraction_config = ExtractionConfig(
    table_name="mi_tabla",
    load_mode=LoadMode.INCREMENTAL,
    max_threads=4,
    chunk_size=10000,
    output_format="parquet",
    raw_storage="s3://mi-bucket/raw-data/"
)

# Crear orquestador
orchestrator = DataExtractionOrchestrator(
    extraction_config=extraction_config,
    process_guid="proceso-123"
)

# Ejecutar extracción
result = orchestrator.execute()

# Verificar resultados
print(f"Registros extraídos: {result.records_extracted}")
print(f"Archivos generados: {result.files_generated}")
print(f"Estado: {result.status}")
```

#### LightTransformOrchestrator

Orquestador para transformaciones ligeras de datos usando PySpark.

```python
from aje_libs.datalake.light_transform import LightTransformOrchestrator
from aje_libs.datalake.light_transform.models import LightTransformConfig

# Configurar transformación
transform_config = LightTransformConfig(
    source_path="s3://mi-bucket/raw-data/",
    target_path="s3://mi-bucket/transformed-data/",
    transformations=[
        {
            "type": "filter",
            "expression": "edad > 18"
        },
        {
            "type": "select",
            "columns": ["nombre", "edad", "email"]
        }
    ]
)

# Crear orquestador
orchestrator = LightTransformOrchestrator(
    transform_config=transform_config
)

# Ejecutar transformación
result = orchestrator.run()

# Verificar resultados
print(f"Registros procesados: {result.records_processed}")
print(f"Estado: {result.status}")
```

## 💡 Ejemplos Prácticos

### Ejemplo 1: Pipeline de Extracción Completo

```python
from aje_libs.datalake.extract_data import DataExtractionOrchestrator
from aje_libs.datalake.extract_data.models import ExtractionConfig
from aje_libs.datalake.shared.models import LoadMode, DatabaseConfig
from aje_libs.common import SecretsHelper, custom_logger

# Configurar logger
logger = custom_logger(__name__)

# Obtener credenciales desde Secrets Manager
secrets = SecretsHelper("prod/database/credentials")
db_config = DatabaseConfig(
    host=secrets.get_secret_value("host"),
    port=int(secrets.get_secret_value("port")),
    database=secrets.get_secret_value("database"),
    username=secrets.get_secret_value("username"),
    password=secrets.get_secret_value("password"),
    db_type="sqlserver"
)

# Configurar extracción
extraction_config = ExtractionConfig(
    table_name="ventas",
    load_mode=LoadMode.INCREMENTAL,
    max_threads=8,
    chunk_size=50000,
    output_format="parquet",
    raw_storage="s3://datalake-raw/ventas/"
)

# Ejecutar
orchestrator = DataExtractionOrchestrator(
    extraction_config=extraction_config,
    process_guid="ventas-2024-01-15"
)

try:
    result = orchestrator.execute()
    logger.info(f"Extracción completada: {result.records_extracted} registros")
except Exception as e:
    logger.error(f"Error en extracción: {e}")
    raise
```

### Ejemplo 2: Procesamiento de Archivos en S3

```python
from aje_libs.common import S3Helper, custom_logger
import json

logger = custom_logger(__name__)

# Inicializar helper
s3 = S3Helper(bucket_name="mi-bucket-datos")

# Listar archivos JSON del último mes
archivos = s3.list_objects_by_last_modified(
    prefix="datos/",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Procesar cada archivo
for archivo in archivos:
    key = archivo['Key']
    logger.info(f"Procesando: {key}")
    
    # Descargar y procesar
    contenido = s3.get_object(key)
    datos = json.loads(contenido['Body'].read())
    
    # Procesar datos...
    # ...
    
    # Subir resultado procesado
    s3.upload_file(
        file_path="/tmp/procesado.json",
        object_key=f"procesados/{key}"
    )
```

### Ejemplo 3: Gestión de Estado en DynamoDB

```python
from aje_libs.common import DynamoDBHelper, custom_logger
from datetime import datetime

logger = custom_logger(__name__)

# Inicializar helper
dynamo = DynamoDBHelper(
    table_name="procesos-estado",
    pk_name="proceso_id",
    sk_name="timestamp"
)

# Registrar inicio de proceso
proceso_id = "proc-123"
timestamp = datetime.now().isoformat()

dynamo.put_item({
    "proceso_id": proceso_id,
    "timestamp": timestamp,
    "estado": "iniciado",
    "inicio": timestamp
})

# Actualizar estado durante procesamiento
dynamo.update_item(
    partition_key=proceso_id,
    sort_key=timestamp,
    update_expression="SET estado = :estado, progreso = :progreso",
    expression_attribute_values={
        ":estado": "procesando",
        ":progreso": 50
    }
)

# Consultar historial del proceso
historial = dynamo.query_items_by_begins_pk_sk(
    partition_key=proceso_id,
    sort_key_portion="",
    limit=100
)
```

## 🧪 Testing con pytest

Esta librería utiliza `pytest` como framework de testing. A continuación se detalla cómo configurar y ejecutar los tests.

### Requisitos Previos

1. **Python 3.9+** instalado
2. **pip** actualizado
3. **Acceso al repositorio** clonado

### Instalación de Dependencias

#### Paso 1: Navegar al directorio del proyecto

```bash
cd aje-libs
```

#### Paso 2: Crear entorno virtual (recomendado)

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**En Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Paso 3: Instalar dependencias

```bash
# Instalar la librería en modo desarrollo
pip install -e .

# Instalar pytest y dependencias de testing
pip install pytest pytest-cov pytest-mock
```

### Estructura de Tests

Los tests están organizados en dos categorías principales:

```
tests/
├── unit/              # Tests unitarios
│   └── datalake/
│       ├── extract_data/
│       ├── light_transform/
│       └── shared/
└── integration/       # Tests de integración
    ├── test_extract_data_local_main.py
    ├── test_extraction_orchestrator_execute.py
    └── test_light_transform_local_main.py
```

### Marcadores de pytest

La librería utiliza marcadores para categorizar los tests:

- `@pytest.mark.unit`: Tests unitarios (rápidos, aislados)
- `@pytest.mark.integration`: Tests de integración (más lentos, requieren recursos)

Estos marcadores están definidos en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: marks tests as unit tests (deselect with '-m \"not unit\"')",
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
```

### Ejecutar Tests

#### Ejecutar todos los tests

```bash
pytest
```

#### Ejecutar solo tests unitarios

```bash
pytest -m unit
```

#### Ejecutar solo tests de integración

```bash
pytest -m integration
```

#### Ejecutar tests de un módulo específico

```bash
# Tests de extract_data
pytest tests/unit/datalake/extract_data/

# Tests de un archivo específico
pytest tests/unit/datalake/extract_data/test_validation_utils.py
```

#### Ejecutar un test específico

```bash
pytest tests/unit/datalake/extract_data/test_validation_utils.py::test_validate_db_type
```

#### Ejecutar con cobertura

```bash
pytest --cov=aje_libs --cov-report=html --cov-report=term
```

Esto generará:
- Un reporte en consola
- Un reporte HTML en `htmlcov/index.html`

#### Ejecutar con verbosidad

```bash
# Verbosidad normal
pytest -v

# Verbosidad máxima
pytest -vv

# Mostrar prints
pytest -s
```

#### Ejecutar en paralelo (requiere pytest-xdist)

```bash
# Instalar pytest-xdist
pip install pytest-xdist

# Ejecutar en paralelo (4 workers)
pytest -n 4
```

### Ejemplos de Tests

#### Test Unitario Simple

```python
import pytest
from aje_libs.datalake.extract_data.utils import validation_utils

@pytest.mark.unit
def test_validate_db_type():
    assert validation_utils.validate_db_type("sqlserver") is True
    assert validation_utils.validate_db_type("unknown") is False
```

#### Test con Parametrización

```python
import pytest
from aje_libs.datalake.extract_data.utils import validation_utils

@pytest.mark.unit
@pytest.mark.parametrize(
    "db_type,expected",
    [
        ("sqlserver", True),
        ("postgresql", True),
        ("unknown", False),
        ("", False),
    ],
)
def test_validate_db_type(db_type, expected):
    assert validation_utils.validate_db_type(db_type) is expected
```

#### Test con Fixtures

```python
import pytest
from aje_libs.datalake.shared.services.logging import LoggerService

@pytest.fixture
def temp_log_dir(tmp_path):
    """Fixture que crea un directorio temporal para logs"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir

@pytest.mark.unit
def test_logger_service(temp_log_dir, monkeypatch):
    # Forzar modo local
    monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
    
    LoggerService.configure_global(
        log_level=logging.INFO,
        log_directory=str(temp_log_dir),
        service_name="test_service",
        force_local_mode=True,
    )
    
    logger = LoggerService.get_logger("test_logger")
    logger.info("mensaje de prueba")
    
    # Verificar que se creó el archivo
    files = list(temp_log_dir.glob("*.log"))
    assert len(files) > 0
```

#### Test con Mocks

```python
import pytest
from unittest.mock import Mock, patch
from aje_libs.common import S3Helper

@pytest.mark.unit
@patch('boto3.client')
def test_s3_helper_upload(mock_boto_client):
    # Crear mock del cliente S3
    mock_s3 = Mock()
    mock_boto_client.return_value = mock_s3
    
    # Crear helper
    helper = S3Helper(bucket_name="test-bucket")
    
    # Ejecutar
    helper.upload_file("local.txt", "remote.txt")
    
    # Verificar que se llamó upload_file
    mock_s3.upload_file.assert_called_once()
```

### Fixtures Disponibles

pytest proporciona varias fixtures útiles:

- `tmp_path`: Directorio temporal para archivos
- `tmpdir`: Directorio temporal (legacy)
- `monkeypatch`: Para modificar variables de entorno y objetos
- `capsys`: Para capturar stdout/stderr
- `mocker`: Para crear mocks (con pytest-mock)

### Configuración Avanzada

#### Archivo pytest.ini (opcional)

Puedes crear un archivo `pytest.ini` en la raíz del proyecto:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
```

#### Variables de Entorno para Tests

Algunos tests pueden requerir variables de entorno. Puedes configurarlas:

```bash
# Windows
set AWS_REGION=us-east-1
set AWS_PROFILE=test-profile
pytest

# Linux/Mac
export AWS_REGION=us-east-1
export AWS_PROFILE=test-profile
pytest
```

O usar un archivo `.env` con `python-dotenv`:

```python
import pytest
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv()
```

### Troubleshooting

#### Error: "No module named 'aje_libs'"

**Solución:** Asegúrate de haber instalado la librería en modo desarrollo:
```bash
pip install -e .
```

#### Error: "Marker 'unit' not found"

**Solución:** Verifica que `pyproject.toml` tenga la configuración de marcadores correcta.

#### Tests de integración fallan

**Solución:** Los tests de integración pueden requerir:
- Credenciales de AWS configuradas
- Recursos de AWS disponibles
- Variables de entorno específicas

Ejecuta solo tests unitarios si no tienes acceso a estos recursos:
```bash
pytest -m "not integration"
```

#### Tests muy lentos

**Solución:** 
- Ejecuta solo tests unitarios: `pytest -m unit`
- Usa paralelización: `pytest -n 4` (con pytest-xdist)
- Ejecuta tests específicos en lugar de toda la suite

### Mejores Prácticas

1. **Nombres descriptivos**: Usa nombres claros para tests (`test_validate_db_type` en lugar de `test1`)

2. **Un test, una aserción**: Cada test debe verificar una cosa específica

3. **Usa fixtures**: Reutiliza código común con fixtures en lugar de duplicar setup

4. **Parametrización**: Usa `@pytest.mark.parametrize` para tests similares

5. **Mocks para dependencias externas**: No dependas de servicios reales en tests unitarios

6. **Tests independientes**: Cada test debe poder ejecutarse de forma aislada

7. **Limpieza**: Usa fixtures con `yield` para limpiar recursos después de los tests

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Estándares de Código

- Sigue PEP 8 para estilo de código Python
- Escribe tests para nuevas funcionalidades
- Actualiza la documentación según sea necesario
- Asegúrate de que todos los tests pasen antes de hacer commit

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👤 Autor

**Miguel Espinoza Alvarez**
- Email: mespinoza1388@gmail.com
- GitHub: [@MR34Z1r0](https://github.com/MR34Z1r0)

## 📚 Recursos Adicionales

- [Documentación de AWS CDK](https://docs.aws.amazon.com/cdk/)
- [Documentación de pytest](https://docs.pytest.org/)
- [Documentación de boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
