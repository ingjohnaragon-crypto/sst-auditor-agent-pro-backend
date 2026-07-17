"""Transformación de `EstandarMinimo` a su DTO de respuesta."""

from src.application.dto.respuesta_estandar_minimo import RespuestaEstandarMinimo
from src.domain.models.estandar_minimo import EstandarMinimo


class MapperEstandarMinimo:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(estandar: EstandarMinimo) -> RespuestaEstandarMinimo:
        """Convierte el ítem del catálogo a su DTO público."""
        return RespuestaEstandarMinimo(
            id=estandar.id,
            ciclo_phva=estandar.ciclo_phva.value,
            numeral=estandar.numeral,
            descripcion=estandar.descripcion,
            valor_porcentual=estandar.valor_porcentual,
        )
