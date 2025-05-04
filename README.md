# CDK AJE Libraries

[![PyPI version](https://badge.fury.io/py/cdk-aje-libs.svg)](https://badge.fury.io/py/cdk-aje-libs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/cdk-aje-libs)](https://pypi.org/project/cdk-aje-libs/)

Biblioteca de utilidades para AWS CDK (Cloud Development Kit) que simplifica la creación y configuración de recursos en entornos AWS.

## Características principales

- **Builders**: Constructores preconfigurados para recursos comunes
- **Constantes**: Definiciones estandarizadas para:
  - Entornos (dev, staging, prod)
  - Rutas comunes
  - Políticas IAM
  - Servicios AWS
- **Modelos**: Configuraciones tipadas para recursos CDK
- **Utils**: Funciones utilitarias para:
  - Manejo de tags
  - Configuraciones repetitivas
  - Buenas prácticas

## Instalación en Producción

```bash
pip install aje-libs
```

## Instalación en Desarrollo
```bash
cd aje-libs/
pip install -e .
```

## Ejemplo de uso

```python
from aws_cdk import App, Stack
from cdk_aje_libs.builders.resource_builder import ResourceBuilder
from cdk_aje_libs.constants.environments import Environment

app = App()
stack = Stack(app, "MyStack")

# Ejemplo de uso de builders
resource_builder = ResourceBuilder(stack, "MyResource", Environment.DEV)
s3_bucket = resource_builder.build_s3_bucket(
    bucket_name="my-example-bucket",
    versioned=True
)

app.synth()
```

Módulos disponibles
Builders
ResourceBuilder: Constructor principal para recursos AWS

NameBuilder: Utilidades para naming conventions

Constantes
Environments: Definición de entornos (dev, staging, prod)

Paths: Rutas comunes para configuraciones

Policies: Políticas IAM predefinidas

Services: Nombres de servicios AWS estandarizados

Models
Configs: Modelos de configuración para recursos CDK

Utils
TagUtils: Funciones para manejo de tags estandarizados
