"""Mappers dominio ↔ DTO para la matriz GTC 45."""

from src.application.dto.matriz_riesgo import (
    RespuestaControlRiesgo,
    RespuestaEvaluacionRiesgo,
    RespuestaPeligro,
    RespuestaPeligroMatriz,
    RespuestaProcesoActividad,
    RespuestaProcesoMatriz,
)
from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad


class MapperMatrizRiesgo:
    """Conversiones puras entre modelos de dominio y DTOs de respuesta."""

    @staticmethod
    def proceso_a_respuesta(proceso: ProcesoActividad) -> RespuestaProcesoActividad:
        assert proceso.id is not None
        return RespuestaProcesoActividad(
            id=proceso.id,
            empresa_id=proceso.empresa_id,
            nombre=proceso.nombre,
            es_rutinaria=proceso.es_rutinaria,
            zona_lugar=proceso.zona_lugar,
            fecha_creacion=proceso.fecha_creacion,
            fecha_actualizacion=proceso.fecha_actualizacion,
        )

    @staticmethod
    def peligro_a_respuesta(peligro: Peligro) -> RespuestaPeligro:
        assert peligro.id is not None
        return RespuestaPeligro(
            id=peligro.id,
            proceso_actividad_id=peligro.proceso_actividad_id,
            clasificacion=peligro.clasificacion.value,
            descripcion=peligro.descripcion,
            efectos_posibles=peligro.efectos_posibles,
            fecha_creacion=peligro.fecha_creacion,
            fecha_actualizacion=peligro.fecha_actualizacion,
        )

    @staticmethod
    def evaluacion_a_respuesta(evaluacion: EvaluacionRiesgo) -> RespuestaEvaluacionRiesgo:
        assert evaluacion.id is not None
        return RespuestaEvaluacionRiesgo(
            id=evaluacion.id,
            peligro_id=evaluacion.peligro_id,
            nivel_deficiencia=evaluacion.nivel_deficiencia,
            nivel_exposicion=evaluacion.nivel_exposicion,
            nivel_consecuencia=evaluacion.nivel_consecuencia,
            nivel_probabilidad=evaluacion.nivel_probabilidad,
            nivel_riesgo=evaluacion.nivel_riesgo,
            interpretacion_nr=evaluacion.interpretacion_nr.value,
            aceptabilidad=evaluacion.aceptabilidad.value,
            fecha_creacion=evaluacion.fecha_creacion,
            fecha_actualizacion=evaluacion.fecha_actualizacion,
        )

    @staticmethod
    def control_a_respuesta(control: ControlRiesgo) -> RespuestaControlRiesgo:
        assert control.id is not None
        return RespuestaControlRiesgo(
            id=control.id,
            evaluacion_riesgo_id=control.evaluacion_riesgo_id,
            tipo=control.tipo.value,
            descripcion=control.descripcion,
            fecha_creacion=control.fecha_creacion,
            fecha_actualizacion=control.fecha_actualizacion,
        )

    @classmethod
    def nodo_peligro_a_respuesta(
        cls,
        peligro: Peligro,
        evaluacion: EvaluacionRiesgo | None,
        controles: list[ControlRiesgo],
    ) -> RespuestaPeligroMatriz:
        return RespuestaPeligroMatriz(
            peligro=cls.peligro_a_respuesta(peligro),
            evaluacion=(cls.evaluacion_a_respuesta(evaluacion) if evaluacion is not None else None),
            controles=[cls.control_a_respuesta(c) for c in controles],
        )

    @classmethod
    def nodo_proceso_a_respuesta(
        cls,
        proceso: ProcesoActividad,
        peligros: list[RespuestaPeligroMatriz],
    ) -> RespuestaProcesoMatriz:
        return RespuestaProcesoMatriz(
            proceso=cls.proceso_a_respuesta(proceso),
            peligros=peligros,
        )
