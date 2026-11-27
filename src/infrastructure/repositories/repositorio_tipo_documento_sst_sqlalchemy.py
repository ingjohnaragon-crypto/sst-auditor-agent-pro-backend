"""Implementación SQLAlchemy del catálogo de tipos documentales PHVA."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.tipo_documento_sst import FaseDocumentoPhva, TipoDocumentoSst
from src.domain.repositories.repositorio_tipo_documento_sst import (
    RepositorioTipoDocumentoSst,
)
from src.infrastructure.database.modelos.tipo_documento_estandar_orm import (
    TipoDocumentoEstandarORM,
)
from src.infrastructure.database.modelos.tipo_documento_sst_orm import TipoDocumentoSstORM

_ORDEN_FASE = {
    FaseDocumentoPhva.PLANEAR.value: 0,
    FaseDocumentoPhva.HACER.value: 1,
    FaseDocumentoPhva.VERIFICAR.value: 2,
    FaseDocumentoPhva.ACTUAR.value: 3,
}


class RepositorioTipoDocumentoSstSQLAlchemy(RepositorioTipoDocumentoSst):
    """Persistencia de lectura del catálogo de tipos."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar(self) -> list[TipoDocumentoSst]:
        filas = (await self._sesion.execute(select(TipoDocumentoSstORM))).scalars().all()
        tipos = [self._a_dominio(fila) for fila in filas]
        tipos.sort(key=lambda t: (_ORDEN_FASE.get(t.fase.value, 99), t.nombre.lower()))
        return tipos

    async def buscar_por_id(self, tipo_id: UUID) -> TipoDocumentoSst | None:
        consulta = select(TipoDocumentoSstORM).where(TipoDocumentoSstORM.id == tipo_id)
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    async def listar_estandares_por_tipo(self, tipo_id: UUID) -> list[UUID]:
        consulta = select(TipoDocumentoEstandarORM.estandar_id).where(
            TipoDocumentoEstandarORM.tipo_id == tipo_id
        )
        return list((await self._sesion.execute(consulta)).scalars().all())

    async def mapear_estandares_por_tipos(self, tipo_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        resultado: dict[UUID, list[UUID]] = {tipo_id: [] for tipo_id in tipo_ids}
        if not tipo_ids:
            return resultado
        consulta = select(
            TipoDocumentoEstandarORM.tipo_id,
            TipoDocumentoEstandarORM.estandar_id,
        ).where(TipoDocumentoEstandarORM.tipo_id.in_(tipo_ids))
        for tipo_id, estandar_id in (await self._sesion.execute(consulta)).all():
            resultado.setdefault(tipo_id, []).append(estandar_id)
        return resultado

    @staticmethod
    def _a_dominio(fila: TipoDocumentoSstORM) -> TipoDocumentoSst:
        return TipoDocumentoSst(
            id=fila.id,
            codigo=fila.codigo,
            nombre=fila.nombre,
            fase=FaseDocumentoPhva(fila.fase),
            descripcion=fila.descripcion,
            obligatorio=fila.obligatorio,
        )
