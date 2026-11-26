"""Cliente S3 compatible con Cloudflare R2 para binarios documentales."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.infrastructure.config.settings import Settings


class AlmacenR2:
    """Guarda, lee y elimina objetos en un bucket R2 vía API S3."""

    def __init__(self, cliente: Any, bucket: str) -> None:
        self._cliente = cliente
        self._bucket = bucket

    def guardar(self, relativa: str, contenido: bytes) -> None:
        """Publica el binario con la clave dada."""
        self._cliente.put_object(Bucket=self._bucket, Key=relativa, Body=contenido)

    def leer(self, relativa: str) -> bytes:
        """Devuelve el binario. Si no existe, FileNotFoundError."""
        try:
            respuesta = self._cliente.get_object(Bucket=self._bucket, Key=relativa)
        except ClientError as exc:
            codigo = exc.response.get("Error", {}).get("Code", "")
            if codigo in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(relativa) from exc
            raise
        cuerpo = respuesta["Body"]
        leer = getattr(cuerpo, "read", None)
        if leer is None:
            raise TypeError("La respuesta de get_object no expone Body.read()")
        return bytes(leer())

    def eliminar(self, relativa: str) -> None:
        """Borra el objeto. No falla si ya no está."""
        self._cliente.delete_object(Bucket=self._bucket, Key=relativa)


def crear_almacen_r2(settings: Settings) -> AlmacenR2:
    """Construye AlmacenR2 o lanza AlmacenamientoNoConfiguradoError sin cliente."""
    if not settings.r2_configurado:
        raise AlmacenamientoNoConfiguradoError()

    # Tras r2_configurado las cinco variables tienen texto.
    assert settings.r2_access_key_id is not None
    assert settings.r2_secret_access_key is not None
    assert settings.r2_bucket is not None
    assert settings.r2_endpoint is not None

    cliente = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    return AlmacenR2(cliente=cliente, bucket=settings.r2_bucket)
