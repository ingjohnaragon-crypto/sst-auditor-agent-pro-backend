"""Casos de uso del repositorio documental de empresa (carga, listado, descarga, borrado)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from src.application.dto.respuesta_archivo_documental import RespuestaArchivoDocumental
from src.application.mappers.mapper_archivo_documental import MapperArchivoDocumental
from src.application.services.servicio_carga_evidencia import (
    MAGIC,
    AlmacenEvidencias,
)
from src.domain.exceptions.archivo_documental import (
    ArchivoInvalidoError,
    ArchivoNoEncontradoError,
    ArchivoObjetoNoDisponibleError,
)
from src.domain.exceptions.autoevaluacion import EmpresaNoEncontradaError
from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.domain.models.archivo_documental import (
    ArchivoDocumental,
    construir_clave_objeto,
    extension_para_mime,
)
from src.domain.models.evidencia import MIME_EXTENSIONES, TAMANO_MAXIMO_BYTES
from src.domain.repositories.repositorio_archivo_documental import (
    RepositorioArchivoDocumental,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario


@dataclass(frozen=True)
class DescargaArchivoDocumental:
    """Binario y metadatos para armar la respuesta HTTP de descarga."""

    contenido: bytes
    tipo_mime: str
    nombre_original: str


class ServicioArchivosDocumentales:
    """Orquesta validación, R2 y metadatos del repositorio documental."""

    def __init__(
        self,
        repositorio: RepositorioArchivoDocumental,
        almacen: AlmacenEvidencias,
        repositorio_usuario: RepositorioUsuario,
        *,
        r2_configurado: bool,
    ) -> None:
        self._repositorio = repositorio
        self._almacen = almacen
        self._repositorio_usuario = repositorio_usuario
        self._r2_configurado = r2_configurado

    async def listar(self, empresa_id: UUID) -> list[RespuestaArchivoDocumental]:
        """Lista archivos de la empresa. 404 si la empresa no existe."""
        await self._exigir_empresa(empresa_id)
        archivos = await self._repositorio.listar_por_empresa(empresa_id)
        return [await self._a_respuesta(archivo) for archivo in archivos]

    async def cargar(
        self,
        empresa_id: UUID,
        nombre: str,
        tipo_mime: str,
        contenido: bytes,
        usuario_id: UUID,
    ) -> RespuestaArchivoDocumental:
        """Valida, sube a R2 y persiste metadatos. Compensa si falla la fila."""
        if not self._r2_configurado:
            raise AlmacenamientoNoConfiguradoError()
        await self._exigir_empresa(empresa_id)
        _exigir_contenido(tipo_mime, contenido)
        mime = tipo_mime.strip().lower()
        extension = extension_para_mime(mime)
        clave = construir_clave_objeto(empresa_id, extension)
        digest = hashlib.sha256(contenido).hexdigest()
        archivo = ArchivoDocumental.crear(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            nombre_original=nombre,
            tipo_mime=mime,
            tamano_bytes=len(contenido),
            hash_contenido=digest,
            clave_objeto=clave,
        )
        self._almacen.guardar(clave, contenido)
        try:
            guardado = await self._repositorio.guardar(archivo)
        except Exception:
            self._almacen.eliminar(clave)
            raise
        return await self._a_respuesta(guardado)

    async def descargar(self, empresa_id: UUID, archivo_id: UUID) -> DescargaArchivoDocumental:
        """Lee el binario del almacén. 404 si falta la fila o el objeto."""
        archivo = await self._obtener_de_empresa(empresa_id, archivo_id)
        try:
            contenido = self._almacen.leer(archivo.clave_objeto)
        except FileNotFoundError as exc:
            raise ArchivoObjetoNoDisponibleError() from exc
        return DescargaArchivoDocumental(
            contenido=contenido,
            tipo_mime=archivo.tipo_mime,
            nombre_original=archivo.nombre_original,
        )

    async def eliminar(self, empresa_id: UUID, archivo_id: UUID) -> None:
        """Borra el objeto en el almacén y la fila (físico)."""
        if not self._r2_configurado:
            raise AlmacenamientoNoConfiguradoError()
        archivo = await self._obtener_de_empresa(empresa_id, archivo_id)
        self._almacen.eliminar(archivo.clave_objeto)
        if archivo.id is not None:
            await self._repositorio.eliminar(archivo.id)

    async def _exigir_empresa(self, empresa_id: UUID) -> None:
        if not await self._repositorio.existe_empresa(empresa_id):
            raise EmpresaNoEncontradaError()

    async def _obtener_de_empresa(self, empresa_id: UUID, archivo_id: UUID) -> ArchivoDocumental:
        await self._exigir_empresa(empresa_id)
        archivo = await self._repositorio.buscar_por_id(archivo_id)
        if archivo is None or archivo.empresa_id != empresa_id:
            raise ArchivoNoEncontradoError()
        return archivo

    async def _a_respuesta(self, archivo: ArchivoDocumental) -> RespuestaArchivoDocumental:
        usuario = await self._repositorio_usuario.buscar_por_id(archivo.usuario_id)
        nombre = usuario.nombre_completo if usuario is not None else None
        return MapperArchivoDocumental.a_respuesta(archivo, usuario_nombre=nombre)


def _exigir_contenido(tipo_mime: str, contenido: bytes) -> None:
    if len(contenido) == 0 or len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ArchivoInvalidoError("El tamaño debe ser mayor que 0 y no superar 10 MiB")
    mime = tipo_mime.strip().lower()
    if mime not in MIME_EXTENSIONES:
        raise ArchivoInvalidoError("El tipo de archivo no está permitido")
    firma = MAGIC.get(mime)
    if firma is None or not contenido.startswith(firma):
        raise ArchivoInvalidoError("El contenido no coincide con el tipo de archivo")


__all__ = [
    "DescargaArchivoDocumental",
    "ServicioArchivosDocumentales",
]
