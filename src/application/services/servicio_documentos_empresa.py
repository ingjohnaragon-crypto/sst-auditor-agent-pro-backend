"""Casos de uso del catálogo documental PHVA por empresa."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.respuesta_documento_empresa import (
    RespuestaDocumentoEmpresa,
    RespuestaTipoDocumentoSst,
)
from src.application.mappers.mapper_documento_empresa import MapperDocumentoEmpresa
from src.application.services.servicio_carga_evidencia import (
    MAGIC,
    AlmacenEvidencias,
)
from src.domain.exceptions.autoevaluacion import EmpresaNoEncontradaError
from src.domain.exceptions.documento_empresa import (
    DocumentoEstadoInvalidoError,
    DocumentoInvalidoError,
    DocumentoNoEncontradoError,
    DocumentoObjetoNoDisponibleError,
    TipoDocumentoNoEncontradoError,
)
from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.domain.models.documento_empresa import (
    DocumentoEmpresa,
    EstadoDocumentoEmpresa,
    construir_clave_documento,
)
from src.domain.models.evidencia import MIME_EXTENSIONES, TAMANO_MAXIMO_BYTES
from src.domain.models.tipo_documento_sst import TipoDocumentoSst
from src.domain.repositories.repositorio_documento_empresa import (
    RepositorioDocumentoEmpresa,
)
from src.domain.repositories.repositorio_tipo_documento_sst import (
    RepositorioTipoDocumentoSst,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario


@dataclass(frozen=True)
class DescargaDocumentoEmpresa:
    """Binario y metadatos para la respuesta HTTP de descarga."""

    contenido: bytes
    tipo_mime: str
    nombre_original: str


class ServicioDocumentosEmpresa:
    """Orquesta catálogo, estados y almacenamiento R2 de documentos PHVA."""

    def __init__(
        self,
        repositorio_documento: RepositorioDocumentoEmpresa,
        repositorio_tipo: RepositorioTipoDocumentoSst,
        almacen: AlmacenEvidencias,
        repositorio_usuario: RepositorioUsuario,
        *,
        r2_configurado: bool,
    ) -> None:
        self._documentos = repositorio_documento
        self._tipos = repositorio_tipo
        self._almacen = almacen
        self._usuarios = repositorio_usuario
        self._r2_configurado = r2_configurado

    async def listar_catalogo(self) -> list[RespuestaTipoDocumentoSst]:
        """Tipos del catálogo con ids de estándares vinculados (puede ser vacío)."""
        tipos = await self._tipos.listar()
        respuestas: list[RespuestaTipoDocumentoSst] = []
        for tipo in tipos:
            if tipo.id is None:
                continue
            estandares = await self._tipos.listar_estandares_por_tipo(tipo.id)
            respuestas.append(MapperDocumentoEmpresa.tipo_a_respuesta(tipo, estandares))
        return respuestas

    async def listar_por_empresa(self, empresa_id: UUID) -> list[RespuestaDocumentoEmpresa]:
        """Un ítem por tipo: fila real o vista PENDIENTE (sin insertar)."""
        await self._exigir_empresa(empresa_id)
        tipos = await self._tipos.listar()
        existentes = {
            doc.tipo_id: doc for doc in await self._documentos.listar_por_empresa(empresa_id)
        }
        respuestas: list[RespuestaDocumentoEmpresa] = []
        for tipo in tipos:
            if tipo.id is None:
                continue
            documento = existentes.get(tipo.id) or DocumentoEmpresa.pendiente(
                empresa_id=empresa_id, tipo_id=tipo.id
            )
            respuestas.append(await self._a_respuesta(documento, tipo))
        return respuestas

    async def cargar(
        self,
        empresa_id: UUID,
        tipo_id: UUID,
        nombre: str,
        tipo_mime: str,
        contenido: bytes,
        usuario_id: UUID,
    ) -> RespuestaDocumentoEmpresa:
        """Valida, sube a R2 y deja el documento en CARGADO (reemplazo soft de clave)."""
        if not self._r2_configurado:
            raise AlmacenamientoNoConfiguradoError()
        await self._exigir_empresa(empresa_id)
        tipo = await self._exigir_tipo(tipo_id)
        _exigir_contenido(tipo_mime, contenido)
        mime = tipo_mime.strip().lower()
        extension = _extension_canonica(mime)
        clave = construir_clave_documento(empresa_id, tipo.codigo, extension)
        existente = await self._documentos.buscar_por_empresa_y_tipo(empresa_id, tipo_id)
        if existente is None:
            documento = DocumentoEmpresa.crear_cargado(
                empresa_id=empresa_id,
                tipo_id=tipo_id,
                usuario_id=usuario_id,
                nombre_original=nombre,
                tipo_mime=mime,
                tamano_bytes=len(contenido),
                clave_objeto=clave,
            )
            clave_anterior = None
        else:
            documento = existente
            clave_anterior = documento.aplicar_carga(
                usuario_id=usuario_id,
                nombre_original=nombre,
                tipo_mime=mime,
                tamano_bytes=len(contenido),
                clave_objeto=clave,
            )
        self._almacen.guardar(clave, contenido)
        try:
            guardado = await self._documentos.guardar(documento)
        except Exception:
            self._almacen.eliminar(clave)
            raise
        if clave_anterior and clave_anterior != clave:
            try:
                self._almacen.eliminar(clave_anterior)
            except Exception:
                pass
        return await self._a_respuesta(guardado, tipo)

    async def descargar(self, empresa_id: UUID, tipo_id: UUID) -> DescargaDocumentoEmpresa:
        """Lee el binario del almacén. 404 si falta fila, clave u objeto."""
        await self._exigir_empresa(empresa_id)
        await self._exigir_tipo(tipo_id)
        documento = await self._documentos.buscar_por_empresa_y_tipo(empresa_id, tipo_id)
        if (
            documento is None
            or documento.estado == EstadoDocumentoEmpresa.PENDIENTE
            or not documento.clave_objeto
            or not documento.tipo_mime
            or not documento.nombre_original
        ):
            raise DocumentoNoEncontradoError()
        try:
            contenido = self._almacen.leer(documento.clave_objeto)
        except FileNotFoundError as exc:
            raise DocumentoObjetoNoDisponibleError() from exc
        return DescargaDocumentoEmpresa(
            contenido=contenido,
            tipo_mime=documento.tipo_mime,
            nombre_original=documento.nombre_original,
        )

    async def marcar_revisado(self, empresa_id: UUID, tipo_id: UUID) -> RespuestaDocumentoEmpresa:
        """Transición CARGADO → REVISADO."""
        await self._exigir_empresa(empresa_id)
        tipo = await self._exigir_tipo(tipo_id)
        documento = await self._documentos.buscar_por_empresa_y_tipo(empresa_id, tipo_id)
        if documento is None or documento.estado == EstadoDocumentoEmpresa.PENDIENTE:
            raise DocumentoEstadoInvalidoError(
                "Solo se puede marcar REVISADO un documento en estado CARGADO"
            )
        documento.marcar_revisado()
        guardado = await self._documentos.guardar(documento)
        return await self._a_respuesta(guardado, tipo)

    async def _exigir_empresa(self, empresa_id: UUID) -> None:
        if not await self._documentos.existe_empresa(empresa_id):
            raise EmpresaNoEncontradaError()

    async def _exigir_tipo(self, tipo_id: UUID) -> TipoDocumentoSst:
        tipo = await self._tipos.buscar_por_id(tipo_id)
        if tipo is None or tipo.id is None:
            raise TipoDocumentoNoEncontradoError()
        return tipo

    async def _a_respuesta(
        self, documento: DocumentoEmpresa, tipo: TipoDocumentoSst
    ) -> RespuestaDocumentoEmpresa:
        nombre = None
        if documento.usuario_id is not None:
            usuario = await self._usuarios.buscar_por_id(documento.usuario_id)
            nombre = usuario.nombre_completo if usuario is not None else None
        return MapperDocumentoEmpresa.documento_a_respuesta(documento, tipo, usuario_nombre=nombre)


_EXTENSION_POR_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def _extension_canonica(tipo_mime: str) -> str:
    try:
        return _EXTENSION_POR_MIME[tipo_mime.strip().lower()]
    except KeyError as exc:
        raise DocumentoInvalidoError("El tipo de archivo no está permitido") from exc


def _exigir_contenido(tipo_mime: str, contenido: bytes) -> None:
    if len(contenido) == 0 or len(contenido) > TAMANO_MAXIMO_BYTES:
        raise DocumentoInvalidoError("El tamaño debe ser mayor que 0 y no superar 10 MiB")
    mime = tipo_mime.strip().lower()
    if mime not in MIME_EXTENSIONES:
        raise DocumentoInvalidoError("El tipo de archivo no está permitido")
    firma = MAGIC.get(mime)
    if firma is None or not contenido.startswith(firma):
        raise DocumentoInvalidoError("El contenido no coincide con el tipo de archivo")


__all__ = [
    "DescargaDocumentoEmpresa",
    "ServicioDocumentosEmpresa",
]
