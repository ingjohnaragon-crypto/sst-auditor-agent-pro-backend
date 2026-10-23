"""Transformación de `AccionMejora` a su DTO de respuesta."""

from src.application.dto.respuesta_accion_mejora import RespuestaAccionMejora
from src.domain.models.accion_mejora import AccionMejora
from src.domain.models.estandar_minimo import EstandarMinimo


class MapperAccionMejora:
    """Mapper estático dominio → DTO. El ítem sale del catálogo."""

    @staticmethod
    def a_respuesta(accion: AccionMejora, estandar: EstandarMinimo) -> RespuestaAccionMejora:
        """Arma la respuesta. Exige que la acción ya tenga id."""
        if accion.id is None:
            msg = "La acción de mejora debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaAccionMejora(
            id=accion.id,
            plan_id=accion.plan_id,
            estandar_id=accion.estandar_id,
            numeral=estandar.numeral,
            descripcion=estandar.descripcion,
            ciclo_phva=accion.ciclo_phva.value,
            responsable_sugerido=accion.responsable_sugerido,
        )
