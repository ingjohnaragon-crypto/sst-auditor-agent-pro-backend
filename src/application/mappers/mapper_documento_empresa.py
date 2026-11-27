"""Mapeo dominio → DTO del catálogo documental PHVA."""

from __future__ import annotations

from uuid import UUID

from src.application.dto.respuesta_documento_empresa import (
    RespuestaDocumentoEmpresa,
    RespuestaTipoDocumentoSst,
)
from src.domain.models.documento_empresa import DocumentoEmpresa
from src.domain.models.tipo_documento_sst import TipoDocumentoSst


class MapperDocumentoEmpresa:
    """Convierte entidades del catálogo a respuestas públicas."""

    @staticmethod
    def tipo_a_respuesta(
        tipo: TipoDocumentoSst,
        estandares_ids: list[UUID] | None = None,
    ) -> RespuestaTipoDocumentoSst:
        if tipo.id is None:
            raise ValueError("El tipo de documento debe tener id persistido")
        return RespuestaTipoDocumentoSst(
            id=tipo.id,
            codigo=tipo.codigo,
            nombre=tipo.nombre,
            fase=tipo.fase.value,
            descripcion=tipo.descripcion,
            obligatorio=tipo.obligatorio,
            estandares_ids=list(estandares_ids or []),
        )

    @staticmethod
    def documento_a_respuesta(
        documento: DocumentoEmpresa,
        tipo: TipoDocumentoSst,
        *,
        usuario_nombre: str | None = None,
    ) -> RespuestaDocumentoEmpresa:
        return RespuestaDocumentoEmpresa(
            id=documento.id,
            empresa_id=documento.empresa_id,
            tipo_id=documento.tipo_id,
            tipo_codigo=tipo.codigo,
            tipo_nombre=tipo.nombre,
            fase=tipo.fase.value,
            estado=documento.estado.value,
            fecha_carga=documento.fecha_carga,
            nombre_original=documento.nombre_original,
            tipo_mime=documento.tipo_mime,
            tamano_bytes=documento.tamano_bytes,
            usuario_nombre=usuario_nombre,
        )
