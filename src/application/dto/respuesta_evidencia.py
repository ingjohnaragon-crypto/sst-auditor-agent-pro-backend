"""DTO de salida de metadatos de una evidencia."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RespuestaEvidencia(BaseModel):
    """Metadatos persistidos de un documento de soporte."""

    id: UUID
    calificacion_estandar_id: UUID
    usuario_id: UUID
    nombre_archivo: str
    tipo_mime: str
    tamano_bytes: int
    ruta_almacenamiento: str
    fecha_carga: datetime
    activo: bool
