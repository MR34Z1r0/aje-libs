# Estrategias de Escritura para Light Transform

Este módulo proporciona estrategias modulares de escritura que se adaptan automáticamente según el `load_type` de la tabla, siguiendo principios SOLID (SRP, OCP).

## 📋 Estrategias Disponibles

### 1. **FullLoadStrategy** (`load_type='full'`)
- **Operación**: OVERWRITE
- **Uso**: Sobrescribe completamente la tabla destino con los nuevos datos
- **Cuándo usar**: 
  - Carga completa inicial
  - Re-carga completa de datos
  - Cuando `load_mode` es `INITIAL` o `RESET` (sobrescribe cualquier otro `load_type`)

**Ejemplo**:
```python
# En tables.csv: LOAD_TYPE=full
# Resultado: OVERWRITE en destino
```

### 2. **IncrementalStrategy** (`load_type='incremental'`)
- **Operación**: MERGE/UPSERT o APPEND
- **Comportamiento**:
  - **MERGE**: Si hay columnas ID marcadas (`is_id=true` en columns.csv) Y la tabla existe
  - **APPEND**: Si no hay columnas ID o es primera carga (tabla no existe)
- **Cuándo usar**: 
  - Cargas incrementales basadas en watermark
  - Actualización de registros existentes
  - Requiere columna de partición para watermark

**Requisitos**:
- Columna de partición (`PARTITION_COLUMN` en tables.csv)
- Configuración de watermark storage (`watermark_storage` en config)
- (Opcional) Columnas ID marcadas para MERGE (`is_id=true` en columns.csv)

**Ejemplo**:
```python
# En tables.csv: LOAD_TYPE=incremental, PARTITION_COLUMN=fecha_proceso
# En columns.csv: is_id=true para columnas ID (ej: id_cliente, id_venta)
# Resultado: MERGE si hay IDs, APPEND si no
```

### 3. **TimeRangeStrategy** (`load_type='time_range'` o `'between-date'`)
- **Operación**: DELETE + INSERT (usando `write_time_range`)
- **Comportamiento**: 
  - Elimina registros de períodos específicos
  - Inserta nuevos datos de esos períodos
- **Cuándo usar**:
  - Reprocesamiento de rangos de tiempo específicos
  - Actualización de períodos históricos
  - Carga por rango de fechas

**Requisitos**:
- Columna de período marcada (`is_process_period=true` en columns.csv) o nombre que contenga 'process_period', 'periodo', 'period', etc.
- Valores del período a procesar (extraídos automáticamente del DataFrame)

**Ejemplo**:
```python
# En tables.csv: LOAD_TYPE=time_range
# En columns.csv: is_process_period=true para columna fecha_proceso
# Resultado: DELETE de períodos específicos + INSERT de nuevos datos
```

## 🔄 Prioridad de Estrategias

La estrategia se determina en este orden:

1. **Load Mode tiene prioridad sobre Load Type**:
   - Si `load_mode` es `INITIAL` o `RESET` → siempre `FullLoadStrategy` (OVERWRITE)
   - Si `load_mode` es `NORMAL` o `REPROCESS` → usa `load_type` para determinar estrategia

2. **Load Type**:
   - `'full'` → `FullLoadStrategy`
   - `'incremental'` → `IncrementalStrategy`
   - `'time_range'` o `'between-date'` → `TimeRangeStrategy`

## ✅ Validación Automática

El sistema incluye validación automática de requisitos antes de ejecutar cada estrategia:

### Validación para IncrementalStrategy
- ✅ Verifica existencia de columnas ID en DataFrame
- ✅ Valida que la tabla destino existe (para MERGE)
- ⚠️ Advertencia si no hay columnas ID pero la tabla existe (usará APPEND)

### Validación para TimeRangeStrategy
- ✅ Verifica que exista columna de período
- ✅ Valida que la columna exista en el DataFrame
- ✅ Extrae valores del período automáticamente
- ❌ Error si no se encuentra columna de período (usa APPEND como fallback)

### Validación para FullLoadStrategy
- ✅ Valida que el DataFrame no sea None
- ⚠️ Advertencia si el DataFrame está vacío

## 🛠️ Uso

### Uso Automático (Recomendado)

El sistema determina automáticamente la estrategia según la configuración de la tabla:

```python
# En DataProcessor, la estrategia se determina automáticamente:
# 1. Lee load_type de TableConfig
# 2. Lee load_mode de LightTransformConfig
# 3. Determina estrategia usando WriteStrategyFactory
# 4. Valida requisitos usando WriteStrategyValidator
# 5. Ejecuta estrategia con parámetros apropiados
```

### Uso Manual (Avanzado)

```python
from aje_libs.datalake.light_transform.strategies import WriteStrategyFactory

# Crear estrategia manualmente
strategy = WriteStrategyFactory.create('incremental')

# Ejecutar estrategia
strategy.execute(
    data_writer=data_writer,
    df=df,
    path='s3://bucket/path',
    partition_cols=['year', 'month'],
    id_columns=['id_cliente', 'id_venta'],
    table_exists=True
)
```

## 🔧 Extensibilidad

Puedes registrar nuevas estrategias personalizadas:

```python
from aje_libs.datalake.light_transform.strategies import WriteStrategyFactory
from aje_libs.datalake.light_transform.contracts.storage import IWriteStrategy

class CustomStrategy(IWriteStrategy):
    def execute(self, data_writer, df, path, partition_cols=None, **kwargs):
        # Tu lógica personalizada
        pass
    
    def get_strategy_name(self) -> str:
        return "custom"
    
    def requires_id_columns(self) -> bool:
        return False
    
    def requires_period_column(self) -> bool:
        return False

# Registrar estrategia personalizada
WriteStrategyFactory.register_strategy('custom', CustomStrategy)
```

## 📊 Compatibilidad con Formatos

Todas las estrategias son compatibles con:
- ✅ **Delta Lake** (`data_writer_type='delta'`)
- ✅ **Apache Iceberg** (`data_writer_type='iceberg'`)
- ✅ **Futuros formatos** (extensible mediante `IDataWriter`)

## 🚨 Manejo de Errores

- **Errores críticos**: Lanzan excepción (`ConfigurationException`)
- **Advertencias**: Se registran pero no detienen la ejecución
- **Fallbacks automáticos**: 
  - `TimeRangeStrategy` sin columna de período → APPEND
  - `IncrementalStrategy` sin columnas ID → APPEND
  - `IncrementalStrategy` sin tabla existente → APPEND (primera carga)

## 📝 Logging

Todas las estrategias incluyen logging detallado:
- 📋 Estrategia seleccionada
- 🔄 Operación ejecutada (MERGE, APPEND, OVERWRITE, DELETE+INSERT)
- ✅ Registros procesados
- ⚠️ Advertencias de validación
- ❌ Errores con contexto detallado

## 🎯 Mejores Prácticas

1. **Para tablas nuevas**: Usar `load_mode=INITIAL` → siempre OVERWRITE
2. **Para cargas incrementales**: 
   - Marcar columnas ID en `columns.csv` (`is_id=true`)
   - Configurar `PARTITION_COLUMN` en `tables.csv`
   - Configurar `watermark_storage` en config
3. **Para reprocesamiento por rango**: 
   - Usar `load_type=time_range`
   - Marcar columna de período (`is_process_period=true`)
4. **Validar configuración**: El sistema valida automáticamente, pero revisa logs para advertencias

