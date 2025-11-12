"""Contrato para la configuración de Light Transform."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional

from aje_libs.datalake.shared.models import LoadMode, ResourceRef


class ILightTransformConfig(ABC):
    """Define los atributos mínimos requeridos para ejecutar Light Transform."""

    @property
    @abstractmethod
    def job_name(self) -> str:
        """Nombre del job (Glue o equivalente)."""

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Nombre lógico de la tabla a procesar."""

    @property
    @abstractmethod
    def load_mode(self) -> LoadMode:
        """Modo de carga (normal, initial, reset, etc.)."""

    @property
    @abstractmethod
    def date_process(self) -> Optional[str]:
        """Fecha de proceso si aplica."""

    @property
    @abstractmethod
    def project_name(self) -> str:
        """Nombre del proyecto."""

    @property
    @abstractmethod
    def team(self) -> str:
        """Equipo responsable."""

    @property
    @abstractmethod
    def data_source(self) -> str:
        """Fuente de datos."""

    @property
    @abstractmethod
    def endpoint_name(self) -> str:
        """Nombre del endpoint origen."""

    @property
    @abstractmethod
    def environment(self) -> str:
        """Ambiente de ejecución."""

    @property
    @abstractmethod
    def source_storage(self) -> ResourceRef:
        """Referencia al almacenamiento origen (RAW)."""

    @property
    @abstractmethod
    def stage_storage(self) -> ResourceRef:
        """Referencia al almacenamiento destino (STAGE)."""

    @property
    @abstractmethod
    def log_storage(self) -> Optional[ResourceRef]:
        """Referencia al almacenamiento de logs."""

    @property
    @abstractmethod
    def watermark_storage(self) -> Optional[ResourceRef]:
        """Referencia al almacenamiento de watermarks."""

    @property
    @abstractmethod
    def config_sources(self) -> Dict[str, ResourceRef]:
        """Mapeo de fuentes de configuración (tables, credentials, columns...)."""

    @property
    @abstractmethod
    def monitor_type(self) -> str:
        """Tipo de monitor a utilizar (dynamodb, console, etc.)."""

    @property
    @abstractmethod
    def config_source_type(self) -> str:
        """Tipo de origen de configuración (csv, database, etc.)."""

    @property
    @abstractmethod
    def data_loader_type(self) -> str:
        """Tipo de loader de datos (spark, jdbc, etc.)."""

    @property
    @abstractmethod
    def data_writer_type(self) -> str:
        """Tipo de writer de datos (delta, parquet, etc.)."""