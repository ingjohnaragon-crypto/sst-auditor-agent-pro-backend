"""Implementación SQLAlchemy de documentos de empresa del catálogo PHVA."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.documento_empresa import DocumentoEmpresa, EstadoDocumentoEmpresa
from src.domain.repositories.repositorio_documento_empresa import (
    RepositorioDocumentoEmpresa,
)
from src.infrastructure.database.modelos.documento_empresa_orm import DocumentoEmpresaORM
from src.infrastructure.database.modelos.empresa_orm import EmpresaORM


class RepositorioDocumentoEmpresaSQLAlchemy(RepositorioDocumentoEmpresa):
    """Persistencia del documento vigente por empresa y tipo."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def existe_empresa(self, empresa_id: UUID) -> bool:
        consulta = select(EmpresaORM.id).where(EmpresaORM.id == empresa_id)
        return (await self._sesion.execute(consulta)).scalar_one_or_none() is not None

    async def listar_por_empresa(self, empresa_id: UUID) -> list[DocumentoEmpresa]:
        consulta = select(DocumentoEmpresaORM).where(DocumentoEmpresaORM.empresa_id == empresa_id)
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def buscar_por_empresa_y_tipo(
        self, empresa_id: UUID, tipo_id: UUID
    ) -> DocumentoEmpresa | None:
        consulta = select(DocumentoEmpresaORM).where(
            DocumentoEmpresaORM.empresa_id == empresa_id,
            DocumentoEmpresaORM.tipo_id == tipo_id,
        )
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    async def guardar(self, documento: DocumentoEmpresa) -> DocumentoEmpresa:
        fila: DocumentoEmpresaORM | None = None
        if documento.id is not None:
            fila = (
                await self._sesion.execute(
                    select(DocumentoEmpresaORM).where(DocumentoEmpresaORM.id == documento.id)
                )
            ).scalar_one_or_none()
        if fila is None:
            fila = (
                await self._sesion.execute(
                    select(DocumentoEmpresaORM).where(
                        DocumentoEmpresaORM.empresa_id == documento.empresa_id,
                        DocumentoEmpresaORM.tipo_id == documento.tipo_id,
                    )
                )
            ).scalar_one_or_none()
        if fila is None:
            fila = DocumentoEmpresaORM(
                id=documento.id if documento.id is not None else uuid4(),
                empresa_id=documento.empresa_id,
                tipo_id=documento.tipo_id,
                estado=documento.estado.value,
                fecha_carga=documento.fecha_carga,
                nombre_original=documento.nombre_original,
                tipo_mime=documento.tipo_mime,
                tamano_bytes=documento.tamano_bytes,
                clave_objeto=documento.clave_objeto,
                usuario_id=documento.usuario_id,
            )
            self._sesion.add(fila)
        else:
            fila.estado = documento.estado.value
            fila.fecha_carga = documento.fecha_carga
            fila.nombre_original = documento.nombre_original
            fila.tipo_mime = documento.tipo_mime
            fila.tamano_bytes = documento.tamano_bytes
            fila.clave_objeto = documento.clave_objeto
            fila.usuario_id = documento.usuario_id
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    @staticmethod
    def _a_dominio(fila: DocumentoEmpresaORM) -> DocumentoEmpresa:
        return DocumentoEmpresa(
            id=fila.id,
            empresa_id=fila.empresa_id,
            tipo_id=fila.tipo_id,
            estado=EstadoDocumentoEmpresa(fila.estado),
            fecha_carga=fila.fecha_carga,
            nombre_original=fila.nombre_original,
            tipo_mime=fila.tipo_mime,
            tamano_bytes=fila.tamano_bytes,
            clave_objeto=fila.clave_objeto,
            usuario_id=fila.usuario_id,
        )
