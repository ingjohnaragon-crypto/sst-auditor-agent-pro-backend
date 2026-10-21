"""Implementación SQLAlchemy del puerto `RepositorioPlanMejora`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.exceptions.plan_mejora import PlanMejoraYaExisteError
from src.domain.models.plan_mejora import ActividadCronograma, PlanMejora
from src.domain.repositories.repositorio_plan_mejora import RepositorioPlanMejora
from src.infrastructure.database.modelos.actividad_cronograma_orm import (
    ActividadCronogramaORM,
)
from src.infrastructure.database.modelos.mes_actividad_orm import MesActividadORM
from src.infrastructure.database.modelos.plan_mejoramiento_orm import PlanMejoramientoORM

_CARGA = selectinload(PlanMejoramientoORM.actividades).selectinload(ActividadCronogramaORM.meses)


class RepositorioPlanMejoraSQLAlchemy(RepositorioPlanMejora):
    """Persistencia de `PlanMejora`. Devuelve dominio, nunca el ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, plan: PlanMejora) -> PlanMejora:
        if plan.id is None:
            plan.id = uuid4()
        fila = await self._cargar(plan.id)
        if fila is None:
            fila = PlanMejoramientoORM(
                id=plan.id,
                empresa_id=plan.empresa_id,
                autoevaluacion_id=plan.autoevaluacion_id,
            )
            self._sesion.add(fila)
        try:
            self._sincronizar_actividades(fila, plan)
            await self._sesion.flush()
        except IntegrityError as exc:
            if "autoevaluacion_id" in str(exc.orig):
                raise PlanMejoraYaExisteError() from exc
            raise
        cargada = await self._cargar(plan.id)
        if cargada is None:
            msg = "El plan no quedó persistido"
            raise RuntimeError(msg)
        return self._a_dominio(cargada)

    async def buscar_por_id(self, id: UUID) -> PlanMejora | None:
        fila = await self._cargar(id)
        return self._a_dominio(fila) if fila is not None else None

    async def buscar_por_autoevaluacion(self, autoevaluacion_id: UUID) -> PlanMejora | None:
        consulta = (
            select(PlanMejoramientoORM)
            .where(PlanMejoramientoORM.autoevaluacion_id == autoevaluacion_id)
            .options(_CARGA)
        )
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    async def eliminar(self, id: UUID) -> None:
        fila = await self._cargar(id)
        if fila is not None:
            await self._sesion.delete(fila)
            await self._sesion.flush()

    async def _cargar(self, id: UUID) -> PlanMejoramientoORM | None:
        consulta = select(PlanMejoramientoORM).where(PlanMejoramientoORM.id == id).options(_CARGA)
        return (await self._sesion.execute(consulta)).scalar_one_or_none()

    @staticmethod
    def _sincronizar_actividades(fila: PlanMejoramientoORM, plan: PlanMejora) -> None:
        por_id = {actividad.id: actividad for actividad in fila.actividades}
        ids: set[UUID] = set()
        for actividad in plan.actividades:
            if actividad.id is None:
                actividad.id = uuid4()
            ids.add(actividad.id)
            existente = por_id.get(actividad.id)
            if existente is None:
                existente = ActividadCronogramaORM(
                    id=actividad.id,
                    plan_mejoramiento_id=fila.id,
                    descripcion=actividad.descripcion,
                    responsable=actividad.responsable,
                    indicador=actividad.indicador,
                )
                fila.actividades.append(existente)
            else:
                existente.descripcion = actividad.descripcion
                existente.responsable = actividad.responsable
                existente.indicador = actividad.indicador
            RepositorioPlanMejoraSQLAlchemy._sincronizar_meses(existente, actividad.meses)
        for orm in list(fila.actividades):
            if orm.id not in ids:
                fila.actividades.remove(orm)

    @staticmethod
    def _sincronizar_meses(fila: ActividadCronogramaORM, meses: tuple[int, ...]) -> None:
        actuales = {mes.mes for mes in fila.meses}
        for mes in meses:
            if mes not in actuales:
                fila.meses.append(MesActividadORM(actividad_id=fila.id, mes=mes))
        esperados = set(meses)
        for orm in list(fila.meses):
            if orm.mes not in esperados:
                fila.meses.remove(orm)

    @staticmethod
    def _a_dominio(fila: PlanMejoramientoORM) -> PlanMejora:
        actividades = [
            ActividadCronograma(
                id=actividad.id,
                descripcion=actividad.descripcion,
                responsable=actividad.responsable,
                indicador=actividad.indicador,
                meses=tuple(sorted(mes.mes for mes in actividad.meses)),
            )
            for actividad in fila.actividades
        ]
        return PlanMejora(
            id=fila.id,
            empresa_id=fila.empresa_id,
            autoevaluacion_id=fila.autoevaluacion_id,
            actividades=actividades,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
