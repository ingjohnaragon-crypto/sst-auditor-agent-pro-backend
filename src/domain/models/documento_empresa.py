"""Documento de empresa por tipo del catálogo PHVA."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from src.domain.exceptions.documento_empresa import (
    DocumentoEstadoInvalidoError,
    DocumentoInvalidoError,
)
from src.domain.models.evidencia import MIME_EXTENSIONES, TAMANO_MAXIMO_BYTES


class EstadoDocumentoEmpresa(StrEnum):
    """Ciclo de vida del documento de empresa para un tipo."""

    PENDIENTE = "PENDIENTE"
    CARGADO = "CARGADO"
    REVISADO = "REVISADO"


class DocumentoEmpresa:
    """Metadatos del documento vigente de un tipo para una empresa (binario en R2)."""

    def __init__(
        self,
        *,
        id: UUID | None,
        empresa_id: UUID,
        tipo_id: UUID,
        estado: EstadoDocumentoEmpresa,
        fecha_carga: datetime | None,
        nombre_original: str | None,
        tipo_mime: str | None,
        tamano_bytes: int | None,
        clave_objeto: str | None,
        usuario_id: UUID | None,
    ) -> None:
        self.id = id
        self.empresa_id = empresa_id
        self.tipo_id = tipo_id
        self.estado = estado
        self.fecha_carga = fecha_carga
        self.nombre_original = nombre_original
        self.tipo_mime = tipo_mime
        self.tamano_bytes = tamano_bytes
        self.clave_objeto = clave_objeto
        self.usuario_id = usuario_id

    @classmethod
    def pendiente(cls, *, empresa_id: UUID, tipo_id: UUID) -> DocumentoEmpresa:
        """Vista sin fila: estado inicial sin clave."""
        return cls(
            id=None,
            empresa_id=empresa_id,
            tipo_id=tipo_id,
            estado=EstadoDocumentoEmpresa.PENDIENTE,
            fecha_carga=None,
            nombre_original=None,
            tipo_mime=None,
            tamano_bytes=None,
            clave_objeto=None,
            usuario_id=None,
        )

    @classmethod
    def crear_cargado(
        cls,
        *,
        empresa_id: UUID,
        tipo_id: UUID,
        usuario_id: UUID,
        nombre_original: str,
        tipo_mime: str,
        tamano_bytes: int,
        clave_objeto: str,
        fecha_carga: datetime | None = None,
    ) -> DocumentoEmpresa:
        """Alta o reemplazo tras una carga válida."""
        nombre = _validar_nombre(nombre_original)
        mime = _validar_mime_y_extension(nombre, tipo_mime)
        _validar_tamano(tamano_bytes)
        clave = _validar_clave_objeto(clave_objeto)
        return cls(
            id=None,
            empresa_id=empresa_id,
            tipo_id=tipo_id,
            estado=EstadoDocumentoEmpresa.CARGADO,
            fecha_carga=fecha_carga or datetime.now(UTC),
            nombre_original=nombre,
            tipo_mime=mime,
            tamano_bytes=tamano_bytes,
            clave_objeto=clave,
            usuario_id=usuario_id,
        )

    def aplicar_carga(
        self,
        *,
        usuario_id: UUID,
        nombre_original: str,
        tipo_mime: str,
        tamano_bytes: int,
        clave_objeto: str,
        fecha_carga: datetime | None = None,
    ) -> str | None:
        """Actualiza metadatos a CARGADO. Devuelve la clave anterior si existía."""
        clave_anterior = self.clave_objeto
        cargado = DocumentoEmpresa.crear_cargado(
            empresa_id=self.empresa_id,
            tipo_id=self.tipo_id,
            usuario_id=usuario_id,
            nombre_original=nombre_original,
            tipo_mime=tipo_mime,
            tamano_bytes=tamano_bytes,
            clave_objeto=clave_objeto,
            fecha_carga=fecha_carga,
        )
        self.estado = cargado.estado
        self.fecha_carga = cargado.fecha_carga
        self.nombre_original = cargado.nombre_original
        self.tipo_mime = cargado.tipo_mime
        self.tamano_bytes = cargado.tamano_bytes
        self.clave_objeto = cargado.clave_objeto
        self.usuario_id = cargado.usuario_id
        return clave_anterior

    def marcar_revisado(self) -> None:
        """Transición CARGADO → REVISADO."""
        if self.estado != EstadoDocumentoEmpresa.CARGADO:
            raise DocumentoEstadoInvalidoError(
                "Solo se puede marcar REVISADO un documento en estado CARGADO"
            )
        self.estado = EstadoDocumentoEmpresa.REVISADO


def construir_clave_documento(empresa_id: UUID, tipo_codigo: str, extension: str) -> str:
    """Clave R2: documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}."""
    codigo = tipo_codigo.strip().upper()
    if not codigo or "/" in codigo or "\\" in codigo:
        raise DocumentoInvalidoError("El código del tipo de documento no es válido")
    ext = extension.strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise DocumentoInvalidoError("La extensión de la clave no está permitida")
    if ext == ".jpeg":
        ext = ".jpg"
    return f"documentos/{empresa_id}/{codigo}/{uuid4()}{ext}"


def _validar_nombre(nombre_original: str) -> str:
    nombre = nombre_original.strip()
    if not nombre or len(nombre) > 255:
        raise DocumentoInvalidoError(
            "El nombre del archivo es obligatorio y máximo de 255 caracteres"
        )
    if "/" in nombre or "\\" in nombre:
        raise DocumentoInvalidoError("El nombre del archivo no puede incluir una ruta")
    if '"' in nombre or "\r" in nombre or "\n" in nombre:
        raise DocumentoInvalidoError(
            "El nombre del archivo no puede incluir comillas ni saltos de línea"
        )
    return nombre


def _validar_mime_y_extension(nombre: str, tipo_mime: str) -> str:
    mime = tipo_mime.strip().lower()
    extensiones = MIME_EXTENSIONES.get(mime)
    if extensiones is None:
        raise DocumentoInvalidoError("El tipo de archivo no está permitido")
    sufijo = PurePosixPath(nombre.lower()).suffix
    if sufijo not in extensiones:
        raise DocumentoInvalidoError("La extensión no coincide con el tipo MIME")
    return mime


def _validar_tamano(tamano_bytes: int) -> None:
    if tamano_bytes <= 0 or tamano_bytes > TAMANO_MAXIMO_BYTES:
        raise DocumentoInvalidoError("El tamaño debe ser mayor que 0 y no superar 10 MiB")


def _validar_clave_objeto(clave_objeto: str) -> str:
    clave = clave_objeto.strip().replace("\\", "/")
    if not clave.startswith("documentos/") or ".." in PurePosixPath(clave).parts:
        raise DocumentoInvalidoError("La clave del objeto no es válida")
    return clave
