"""Transformación de `ArchivoDocumental` a su DTO de respuesta."""

from src.application.dto.respuesta_archivo_documental import RespuestaArchivoDocumental
from src.domain.models.archivo_documental import ArchivoDocumental


class MapperArchivoDocumental:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(
        archivo: ArchivoDocumental,
        *,
        usuario_nombre: str | None = None,
    ) -> RespuestaArchivoDocumental:
        """Convierte el metadato persistido a su DTO público (sin clave_objeto)."""
        if archivo.id is None:
            msg = "El archivo debe tener id asignado para mapearse a respuesta"
            raise ValueError(msg)
        return RespuestaArchivoDocumental(
            id=archivo.id,
            empresa_id=archivo.empresa_id,
            nombre_original=archivo.nombre_original,
            tipo_mime=archivo.tipo_mime,
            tamano_bytes=archivo.tamano_bytes,
            fecha_carga=archivo.fecha_carga,
            usuario_id=archivo.usuario_id,
            usuario_nombre=usuario_nombre,
        )
