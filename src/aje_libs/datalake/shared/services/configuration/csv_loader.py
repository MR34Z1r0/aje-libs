"""
Implementaciones de ICsvLoader para diferentes orígenes (S3, local, etc.).
"""
from __future__ import annotations

import os
from typing import Dict

import boto3

from aje_libs.datalake.shared.contracts.configuration import ICsvLoader


class LocalCsvLoader(ICsvLoader):
    """Carga CSV desde el sistema de archivos local (ruta absoluta o file://)."""

    def load(self, path: str) -> str:
        normalized = path
        if normalized.startswith("file://"):
            normalized = normalized[7:]
        with open(normalized, "r", encoding="latin1") as handler:
            return handler.read()


class S3CsvLoader(ICsvLoader):
    """Carga CSV desde S3 utilizando boto3."""

    def __init__(self, s3_client=None):
        self.s3_client = s3_client or boto3.client("s3")

    def load(self, path: str) -> str:
        if not path.startswith("s3://"):
            raise ValueError(f"Ruta S3 inválida: {path}")

        bucket = path.split("/")[2]
        key = "/".join(path.split("/")[3:])
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("latin1")


class MultiSourceCsvLoader(ICsvLoader):
    """
    Delegador que soporta múltiples esquemas de ruta.
    Permite agregar fácilmente nuevos orígenes (gs://, abfs://, etc.).
    """

    def __init__(self, loaders: Dict[str, ICsvLoader], default_loader: ICsvLoader):
        self.loaders = loaders
        self.default_loader = default_loader

    def load(self, path: str) -> str:
        if "://" in path:
            scheme = path.split("://", 1)[0]
            if scheme in self.loaders:
                return self.loaders[scheme].load(path)
        return self.default_loader.load(path)


def build_default_csv_loader() -> ICsvLoader:
    """
    Crea un loader multi-origen con soporte para S3 y archivos locales por defecto.
    """
    local_loader = LocalCsvLoader()
    s3_loader = S3CsvLoader()
    return MultiSourceCsvLoader(
        loaders={
            "s3": s3_loader,
            "file": local_loader,
        },
        default_loader=local_loader,
    )


__all__ = [
    "ICsvLoader",
    "LocalCsvLoader",
    "S3CsvLoader",
    "MultiSourceCsvLoader",
    "build_default_csv_loader",
]

