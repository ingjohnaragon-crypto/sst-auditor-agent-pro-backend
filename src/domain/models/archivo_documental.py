"""Metadatos de un archivo documental de empresa — sin el binario."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from src.domain.exceptions.archivo_documental import ArchivoInvalidoError
from src.domain.models.evidencia import MIME_EXTENSIONES, TAMANO_MAXIMO_BYTES

ESQUEMAS_PROHIBIDOS = ("http://", "https://", "file://", "file:")
_HASH_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_EXTENSION_POR_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@dataclass
class ArchivoDocumental:
    """Ubicación R2 y atributos de un documento de la empresa."""

    id: UUID | None
    empresa_id: UUID
    nombre_original: str
    tipo_mime: str
    tamano_bytes: int
    hash: str
    clave_objeto: str
    usuario_id: UUID
    fecha_carga: datetime
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        empresa_id: UUID,
        usuario_id: UUID,
        nombre_original: str,
        tipo_mime: str,
        tamano_bytes: int,
        hash_contenido: str,
        clave_objeto: str,
    ) -> ArchivoDocumental:
        """Valida tipo, tamaño, hash y clave R2 antes de construir el metadato."""
        nombre = _validar_nombre(nombre_original)
        mime = _validar_mime_y_extension(nombre, tipo_mime)
        tamano = _validar_tamano(tamano_bytes)
        digest = _validar_hash(hash_contenido)
        clave = _validar_clave_objeto(clave_objeto)
        ahora = datetime.now(UTC)
        return cls(
            id=None,
            empresa_id=empresa_id,
            nombre_original=nombre,
            tipo_mime=mime,
            tamano_bytes=tamano,
            hash=digest,
            clave_objeto=clave,
            usuario_id=usuario_id,
            fecha_carga=ahora,
            fecha_creacion=ahora,
            fecha_actualizacion=ahora,
        )


def construir_clave_objeto(empresa_id: UUID, extension: str) -> str:
    """Arma una clave R2 única: evidencias/{empresa_id}/{uuid}{ext}."""
    ext = extension.strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise ArchivoInvalidoError("La extensión de la clave no está permitida")
    if ext == ".jpeg":
        ext = ".jpg"
    return f"evidencias/{empresa_id}/{uuid4()}{ext}"


def extension_para_mime(tipo_mime: str) -> str:
    """Devuelve la extensión canónica del MIME permitido."""
    mime = tipo_mime.strip().lower()
    try:
        return _EXTENSION_POR_MIME[mime]
    except KeyError as exc:
        raise ArchivoInvalidoError("El tipo de archivo no está permitido") from exc


def _validar_nombre(nombre_original: str) -> str:
    nombre = nombre_original.strip()
    if not nombre or len(nombre) > 255:
        raise ArchivoInvalidoError(
            "El nombre del archivo es obligatorio y máximo de 255 caracteres"
        )
    if "/" in nombre or "\\" in nombre:
        raise ArchivoInvalidoError("El nombre del archivo no puede incluir una ruta")
    return nombre


def _validar_mime_y_extension(nombre: str, tipo_mime: str) -> str:
    mime = tipo_mime.strip().lower()
    extensiones = MIME_EXTENSIONES.get(mime)
    if extensiones is None:
        raise ArchivoInvalidoError("El tipo de archivo no está permitido")
    sufijo = PurePosixPath(nombre.lower()).suffix
    if sufijo not in extensiones:
        raise ArchivoInvalidoError("La extensión no coincide con el tipo MIME")
    return mime


def _validar_tamano(tamano_bytes: int) -> int:
    if tamano_bytes <= 0 or tamano_bytes > TAMANO_MAXIMO_BYTES:
        raise ArchivoInvalidoError("El tamaño debe ser mayor que 0 y no superar 10 MiB")
    return tamano_bytes


def _validar_hash(hash_contenido: str) -> str:
    digest = hash_contenido.strip().lower()
    if not _HASH_SHA256.fullmatch(digest):
        raise ArchivoInvalidoError("El hash debe ser SHA-256 en hexadecimal (64 caracteres)")
    return digest


def _validar_clave_objeto(clave_objeto: str) -> str:
    """Clave R2: identificador de objeto, no ruta de disco del servidor."""
    clave = clave_objeto.strip().replace("\\", "/")
    if not clave:
        raise ArchivoInvalidoError("La clave de objeto es obligatoria")
    minuscula = clave.lower()
    if any(minuscula.startswith(esquema) for esquema in ESQUEMAS_PROHIBIDOS):
        raise ArchivoInvalidoError("La clave de objeto no puede incluir un esquema")
    if clave.startswith("/") or ":" in clave:
        raise ArchivoInvalidoError("La clave de objeto no puede ser absoluta")
    if len(clave) > 500:
        raise ArchivoInvalidoError("La clave de objeto supera 500 caracteres")
    return clave
