# Cómo empaquetar y usar aje_libs en AWS Glue

Este documento explica cómo empaquetar la librería `aje_libs` y usarla en jobs de AWS Glue.

## 📦 Empaquetado

### Opción 1: Usando el script Python (Recomendado)

```bash
cd aje-libs
python package_for_glue.py
```

### Opción 2: Usando el script Batch (Windows)

```cmd
cd aje-libs
package_for_glue.bat
```

### ¿Qué hace el script?

1. **Toma el código fuente** de `aje-libs/src/aje_libs`
2. **Limpia archivos innecesarios** (`__pycache__`, `.pyc`, etc.)
3. **Crea un zip** con la estructura correcta para Glue:
   ```
   aje_libs.zip
   └── aje_libs/
       ├── __init__.py
       ├── common/
       ├── datalake/
       └── ...
   ```
4. **Coloca el zip** en `cdk-datalake-ingest-bigmagic/artifacts/aws-glue/layer/aje_libs.zip`

## 🚀 Despliegue a AWS

### Automático (con CDK)

El archivo `aje_libs.zip` se sube automáticamente a S3 cuando ejecutas:

```bash
cd cdk-datalake-ingest-bigmagic
cdk deploy
```

El CDK está configurado para:
- Tomar el contenido de `artifacts/aws-glue/layer/`
- Subirlo a S3 en la ruta: `{team}/{datasource}/aws-glue/layer/aje_libs.zip`

### Manual (si necesitas subirlo directamente)

```bash
aws s3 cp artifacts/aws-glue/layer/aje_libs.zip \
  s3://{bucket-name}/{team}/{datasource}/aws-glue/layer/aje_libs.zip
```

## 🔧 Uso en Jobs de Glue

Los jobs de Glue ya están configurados para usar `aje_libs.zip` mediante el parámetro `--extra-py-files`:

```python
default_arguments={
    '--extra-py-files': f"s3://{bucket}/{team}/{datasource}/aws-glue/layer/aje_libs.zip",
    # ... otros parámetros
}
```

### Verificación en el código Glue

En tu código de Glue (`extract_data_glue.py`), simplemente importa:

```python
from aje_libs.datalake.extract_data.orchestrators.extraction_orchestrator import (
    DataExtractionOrchestrator,
)
from aje_libs.datalake.shared.services.logging import LoggerService
# ... etc
```

## 📝 Flujo de trabajo recomendado

1. **Desarrollar** cambios en `aje-libs/src/aje_libs/`
2. **Probar localmente** (usando `pip install -e .` en modo desarrollo)
3. **Empaquetar** para Glue:
   ```bash
   cd aje-libs
   python package_for_glue.py
   ```
4. **Desplegar** con CDK:
   ```bash
   cd ../cdk-datalake-ingest-bigmagic
   cdk deploy
   ```
5. **Ejecutar** el job de Glue para verificar que funciona

## ⚠️ Notas importantes

- **Tamaño del zip**: AWS Glue tiene límites de tamaño para `--extra-py-files`. Si el zip es muy grande (>250MB), considera usar Glue Python libraries o separar dependencias.
- **Dependencias**: Las dependencias externas (como `aws-lambda-powertools`, `pymssql`) se instalan mediante `--additional-python-modules` en la configuración del job.
- **Estructura del zip**: El zip debe tener la estructura `aje_libs/` en la raíz, no `src/aje_libs/`.
- **Actualizaciones**: Cada vez que cambies código en `aje_libs`, debes re-empacar y re-desplegar.

## 🐛 Solución de problemas

### Error: "No module named 'aje_libs'"

1. Verifica que el zip se subió correctamente a S3
2. Verifica que la ruta en `--extra-py-files` es correcta
3. Verifica que el zip tiene la estructura correcta (`aje_libs/` en la raíz)

### Error: "ModuleNotFoundError: No module named 'X'"

1. Verifica que las dependencias están en `--additional-python-modules`
2. Algunas dependencias pueden requerir compilación nativa y no funcionar en Glue

### El zip es muy grande

1. Revisa si hay archivos innecesarios (`.pyc`, `__pycache__`, etc.)
2. Considera usar Glue Python libraries para dependencias grandes
3. Separa dependencias opcionales en zips diferentes

