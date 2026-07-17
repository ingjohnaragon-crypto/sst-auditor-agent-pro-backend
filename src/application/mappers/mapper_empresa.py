"""Transformación de la entidad `Empresa` a su DTO de respuesta."""

from src.application.dto.respuesta_empresa import RespuestaEmpresa
from src.domain.models.empresa import Empresa


class MapperEmpresa:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(empresa: Empresa) -> RespuestaEmpresa:
        """Convierte la entidad persistida a su DTO público."""
        if empresa.id is None:
            msg = "La empresa debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaEmpresa(
            id=empresa.id,
            razon_social=empresa.razon_social,
            nit=empresa.nit,
            actividad_economica=empresa.actividad_economica,
            nivel_riesgo_arl=empresa.nivel_riesgo_arl,
            numero_trabajadores=empresa.numero_trabajadores,
            fecha_creacion=empresa.fecha_creacion,
            fecha_actualizacion=empresa.fecha_actualizacion,
        )
