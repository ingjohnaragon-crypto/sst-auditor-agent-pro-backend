"""Transformación del agregado `PlanMejora` a su DTO de respuesta."""

from src.application.dto.respuesta_plan_mejora import (
    RespuestaActividadCronograma,
    RespuestaPlanMejora,
)
from src.domain.models.plan_mejora import ActividadCronograma, PlanMejora


class MapperPlanMejora:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(plan: PlanMejora) -> RespuestaPlanMejora:
        """Convierte el plan. Exige id en el plan y en cada actividad."""
        if plan.id is None:
            msg = "El plan de mejora debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaPlanMejora(
            id=plan.id,
            empresa_id=plan.empresa_id,
            autoevaluacion_id=plan.autoevaluacion_id,
            actividades=[MapperPlanMejora._actividad(item) for item in plan.actividades],
        )

    @staticmethod
    def _actividad(actividad: ActividadCronograma) -> RespuestaActividadCronograma:
        if actividad.id is None:
            msg = "La actividad debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaActividadCronograma(
            id=actividad.id,
            descripcion=actividad.descripcion,
            responsable=actividad.responsable,
            indicador=actividad.indicador,
            meses=list(actividad.meses),
        )
