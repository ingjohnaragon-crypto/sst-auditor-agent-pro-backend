"""DTO de salida de metadatos de un archivo documental de empresa."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RespuestaArchivoDocumental(BaseModel):
    """Metadatos públicos de un documento de empresa (sin clave R2)."""

    id: UUID
    empresa_id: UUID
    nombre_original: str
    tipo_mime: str
    tamano_bytes: int
    fecha_carga: datetime
    usuario_id: UUID
    usuario_nombre: str | None = None
