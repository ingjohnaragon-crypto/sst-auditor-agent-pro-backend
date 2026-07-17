"""Transformación del agregado `Autoevaluacion` a sus DTOs de respuesta."""

from src.application.dto.respuesta_autoevaluacion import RespuestaAutoevaluacion
from src.application.dto.respuesta_calificacion_estandar import (
    RespuestaCalificacionEstandar,
)
from src.domain.models.autoevaluacion import Autoevaluacion, CalificacionEstandar


class MapperAutoevaluacion:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta_calificacion(
        calificacion: CalificacionEstandar,
    ) -> RespuestaCalificacionEstandar:
        """Convierte una calificación a su DTO público."""
        return RespuestaCalificacionEstandar(
            estandar_id=calificacion.estandar_id,
            resultado=calificacion.resultado.value,
            puntaje=calificacion.puntaje,
            observaciones=calificacion.observaciones,
        )

    @staticmethod
    def a_respuesta(
        autoevaluacion: Autoevaluacion,
        *,
        incluir_calificaciones: bool = True,
    ) -> RespuestaAutoevaluacion:
        """Convierte el agregado a su DTO; el listado histórico omite calificaciones."""
        if autoevaluacion.id is None:
            msg = "La autoevaluación debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        calificaciones: list[RespuestaCalificacionEstandar] = []
        if incluir_calificaciones:
            calificaciones = [
                MapperAutoevaluacion.a_respuesta_calificacion(c)
                for c in autoevaluacion.calificaciones.values()
            ]
        return RespuestaAutoevaluacion(
            id=autoevaluacion.id,
            empresa_id=autoevaluacion.empresa_id,
            usuario_id=autoevaluacion.usuario_id,
            fecha=autoevaluacion.fecha,
            puntaje_total=autoevaluacion.puntaje_total,
            requiere_plan_mejora=autoevaluacion.requiere_plan_mejora,
            calificaciones=calificaciones,
            fecha_creacion=autoevaluacion.fecha_creacion,
            fecha_actualizacion=autoevaluacion.fecha_actualizacion,
        )
