"""Implementación SQLAlchemy del puerto `RepositorioArchivoDocumental`."""

from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.archivo_documental import ArchivoDocumental
from src.domain.repositories.repositorio_archivo_documental import (
    RepositorioArchivoDocumental,
)
from src.infrastructure.database.modelos.archivo_documental_orm import ArchivoDocumentalORM
from src.infrastructure.database.modelos.empresa_orm import EmpresaORM


class RepositorioArchivoDocumentalSQLAlchemy(RepositorioArchivoDocumental):
    """Persistencia de metadatos de archivos documentales."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, archivo: ArchivoDocumental) -> ArchivoDocumental:
        fila = ArchivoDocumentalORM(
            id=archivo.id if archivo.id is not None else uuid4(),
            empresa_id=archivo.empresa_id,
            nombre_original=archivo.nombre_original,
            tipo_mime=archivo.tipo_mime,
            tamano_bytes=archivo.tamano_bytes,
            hash=archivo.hash,
            clave_objeto=archivo.clave_objeto,
            usuario_id=archivo.usuario_id,
            fecha_carga=archivo.fecha_carga,
        )
        self._sesion.add(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def listar_por_empresa(self, empresa_id: UUID) -> list[ArchivoDocumental]:
        consulta = (
            select(ArchivoDocumentalORM)
            .where(ArchivoDocumentalORM.empresa_id == empresa_id)
            .order_by(ArchivoDocumentalORM.fecha_carga.desc())
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def buscar_por_id(self, id: UUID) -> ArchivoDocumental | None:
        fila = await self._obtener_fila(id)
        return self._a_dominio(fila) if fila is not None else None

    async def eliminar(self, id: UUID) -> None:
        await self._sesion.execute(
            delete(ArchivoDocumentalORM).where(ArchivoDocumentalORM.id == id)
        )
        await self._sesion.flush()

    async def existe_empresa(self, empresa_id: UUID) -> bool:
        consulta = select(EmpresaORM.id).where(EmpresaORM.id == empresa_id)
        return (await self._sesion.execute(consulta)).scalar_one_or_none() is not None

    async def _obtener_fila(self, id: UUID) -> ArchivoDocumentalORM | None:
        consulta = select(ArchivoDocumentalORM).where(ArchivoDocumentalORM.id == id)
        return (await self._sesion.execute(consulta)).scalar_one_or_none()

    @staticmethod
    def _a_dominio(fila: ArchivoDocumentalORM) -> ArchivoDocumental:
        return ArchivoDocumental(
            id=fila.id,
            empresa_id=fila.empresa_id,
            nombre_original=fila.nombre_original,
            tipo_mime=fila.tipo_mime,
            tamano_bytes=fila.tamano_bytes,
            hash=fila.hash,
            clave_objeto=fila.clave_objeto,
            usuario_id=fila.usuario_id,
            fecha_carga=fila.fecha_carga,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
