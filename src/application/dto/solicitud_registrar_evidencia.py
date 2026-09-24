"""DTO de entrada para registrar metadatos de una evidencia."""

from pydantic import BaseModel, ConfigDict


class SolicitudRegistrarEvidencia(BaseModel):
    """Metadatos del adjunto. `usuario_id` no se acepta: sale del Bearer."""

    model_config = ConfigDict(extra="forbid")

    nombre_archivo: str
    tipo_mime: str
    tamano_bytes: int
    ruta_almacenamiento: str
