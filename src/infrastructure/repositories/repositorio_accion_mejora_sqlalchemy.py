"""Implementación SQLAlchemy del puerto `RepositorioAccionMejora`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.accion_mejora import AccionMejora
from src.domain.models.estandar_minimo import CicloPHVA
from src.domain.repositories.repositorio_accion_mejora import RepositorioAccionMejora
from src.infrastructure.database.modelos.accion_mejora_orm import AccionMejoraORM


class RepositorioAccionMejoraSQLAlchemy(RepositorioAccionMejora):
    """Persistencia del borrador. Devuelve dominio, nunca el ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar_por_plan(self, plan_id: UUID) -> list[AccionMejora]:
        consulta = select(AccionMejoraORM).where(AccionMejoraORM.plan_mejoramiento_id == plan_id)
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def guardar(self, accion: AccionMejora) -> AccionMejora:
        if accion.id is None:
            accion.id = uuid4()
        fila = AccionMejoraORM(
            id=accion.id,
            plan_mejoramiento_id=accion.plan_id,
            estandar_minimo_id=accion.estandar_id,
            ciclo_phva=accion.ciclo_phva.value,
            responsable_sugerido=accion.responsable_sugerido,
        )
        try:
            async with self._sesion.begin_nested():
                self._sesion.add(fila)
                await self._sesion.flush()
        except IntegrityError as exc:
            if not _es_duplicado(exc):
                raise
            existente = await self._buscar(accion.plan_id, accion.estandar_id)
            if existente is None:
                raise
            return existente
        return accion

    async def _buscar(self, plan_id: UUID, estandar_id: UUID) -> AccionMejora | None:
        consulta = select(AccionMejoraORM).where(
            AccionMejoraORM.plan_mejoramiento_id == plan_id,
            AccionMejoraORM.estandar_minimo_id == estandar_id,
        )
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    @staticmethod
    def _a_dominio(fila: AccionMejoraORM) -> AccionMejora:
        return AccionMejora(
            id=fila.id,
            plan_id=fila.plan_mejoramiento_id,
            estandar_id=fila.estandar_minimo_id,
            ciclo_phva=CicloPHVA(fila.ciclo_phva),
            responsable_sugerido=fila.responsable_sugerido,
        )


def _es_duplicado(exc: IntegrityError) -> bool:
    texto = str(exc.orig)
    return "uq_acciones_mejora_plan_estandar" in texto or "estandar_minimo_id" in texto
