"""Transformación de `Evidencia` a su DTO de respuesta."""

from src.application.dto.respuesta_evidencia import RespuestaEvidencia
from src.domain.models.evidencia import Evidencia


class MapperEvidencia:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(evidencia: Evidencia) -> RespuestaEvidencia:
        """Convierte el metadato persistido a su DTO público."""
        if evidencia.id is None:
            msg = "La evidencia debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaEvidencia(
            id=evidencia.id,
            calificacion_estandar_id=evidencia.calificacion_estandar_id,
            usuario_id=evidencia.usuario_id,
            nombre_archivo=evidencia.nombre_archivo,
            tipo_mime=evidencia.tipo_mime,
            tamano_bytes=evidencia.tamano_bytes,
            ruta_almacenamiento=evidencia.ruta_almacenamiento,
            fecha_carga=evidencia.fecha_carga,
            activo=evidencia.activo,
        )
