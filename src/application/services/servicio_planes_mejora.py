"""Casos de uso del plan de mejora. Sin FastAPI ni SQLAlchemy."""

from uuid import UUID

from src.application.dto.respuesta_plan_mejora import RespuestaPlanMejora
from src.application.dto.solicitud_plan_mejora import (
    SolicitudAbrirPlanMejora,
    SolicitudActividadCronograma,
)
from src.application.mappers.mapper_plan_mejora import MapperPlanMejora
from src.domain.exceptions.autoevaluacion import AutoevaluacionNoEncontradaError
from src.domain.exceptions.plan_mejora import (
    PlanMejoraNoEncontradoError,
    PlanMejoraYaExisteError,
)
from src.domain.models.plan_mejora import PlanMejora
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_plan_mejora import RepositorioPlanMejora


class ServicioPlanesMejora:
    """Abre, consulta y edita el plan ligado a una autoevaluación."""

    def __init__(
        self,
        repositorio_plan: RepositorioPlanMejora,
        repositorio_autoevaluacion: RepositorioAutoevaluacion,
    ) -> None:
        self._planes = repositorio_plan
        self._autoevaluaciones = repositorio_autoevaluacion

    async def abrir(
        self,
        autoevaluacion_id: UUID,
        solicitud: SolicitudAbrirPlanMejora,
    ) -> RespuestaPlanMejora:
        """Crea el plan con `PlanMejora.crear`. No recalcula el umbral de 85."""
        autoevaluacion = await self._autoevaluaciones.buscar_por_id(autoevaluacion_id)
        if autoevaluacion is None:
            raise AutoevaluacionNoEncontradaError()
        existente = await self._planes.buscar_por_autoevaluacion(autoevaluacion_id)
        if existente is not None:
            raise PlanMejoraYaExisteError()
        plan = PlanMejora.crear(autoevaluacion)
        for actividad in solicitud.actividades:
            plan.agregar_actividad(
                actividad.descripcion,
                actividad.responsable,
                actividad.indicador,
                actividad.meses,
            )
        guardado = await self._planes.guardar(plan)
        return MapperPlanMejora.a_respuesta(guardado)

    async def obtener_por_autoevaluacion(self, autoevaluacion_id: UUID) -> RespuestaPlanMejora:
        """Plan de esa autoevaluación, o 404 si aún no se abrió."""
        plan = await self._planes.buscar_por_autoevaluacion(autoevaluacion_id)
        if plan is None:
            raise PlanMejoraNoEncontradoError()
        return MapperPlanMejora.a_respuesta(plan)

    async def obtener(self, plan_id: UUID) -> RespuestaPlanMejora:
        """Detalle del plan por su id."""
        return MapperPlanMejora.a_respuesta(await self._exigir(plan_id))

    async def agregar_actividad(
        self,
        plan_id: UUID,
        solicitud: SolicitudActividadCronograma,
    ) -> RespuestaPlanMejora:
        """Agrega una actividad y devuelve el plan completo."""
        plan = await self._exigir(plan_id)
        plan.agregar_actividad(
            solicitud.descripcion,
            solicitud.responsable,
            solicitud.indicador,
            solicitud.meses,
        )
        guardado = await self._planes.guardar(plan)
        return MapperPlanMejora.a_respuesta(guardado)

    async def actualizar_actividad(
        self,
        plan_id: UUID,
        actividad_id: UUID,
        solicitud: SolicitudActividadCronograma,
    ) -> RespuestaPlanMejora:
        """Reemplaza los datos de la actividad y conserva su id."""
        plan = await self._exigir(plan_id)
        plan.actualizar_actividad(
            actividad_id,
            solicitud.descripcion,
            solicitud.responsable,
            solicitud.indicador,
            solicitud.meses,
        )
        guardado = await self._planes.guardar(plan)
        return MapperPlanMejora.a_respuesta(guardado)

    async def quitar_actividad(self, plan_id: UUID, actividad_id: UUID) -> None:
        """Quita la actividad y persiste el plan."""
        plan = await self._exigir(plan_id)
        plan.quitar_actividad(actividad_id)
        await self._planes.guardar(plan)

    async def eliminar(self, plan_id: UUID) -> None:
        """Borra el plan. 404 si no existe."""
        await self._exigir(plan_id)
        await self._planes.eliminar(plan_id)

    async def _exigir(self, plan_id: UUID) -> PlanMejora:
        plan = await self._planes.buscar_por_id(plan_id)
        if plan is None:
            raise PlanMejoraNoEncontradoError()
        return plan
