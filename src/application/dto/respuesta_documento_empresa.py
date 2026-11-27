"""DTOs de respuesta del catálogo documental PHVA."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RespuestaTipoDocumentoSst(BaseModel):
    """Tipo del catálogo (sin secretos de almacenamiento)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    nombre: str
    fase: str
    descripcion: str
    obligatorio: bool
    estandares_ids: list[UUID] = Field(default_factory=list)


class RespuestaDocumentoEmpresa(BaseModel):
    """Estado del documento por tipo; nunca incluye clave_objeto."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    empresa_id: UUID
    tipo_id: UUID
    tipo_codigo: str
    tipo_nombre: str
    fase: str
    estado: str
    fecha_carga: datetime | None = None
    nombre_original: str | None = None
    tipo_mime: str | None = None
    tamano_bytes: int | None = None
    usuario_nombre: str | None = None


class SolicitudMarcarDocumento(BaseModel):
    """Cuerpo PATCH para marcar REVISADO."""

    estado: str = Field(..., examples=["REVISADO"])
