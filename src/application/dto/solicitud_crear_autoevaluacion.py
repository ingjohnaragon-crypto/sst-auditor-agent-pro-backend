"""DTO de entrada para crear una autoevaluación."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SolicitudCrearAutoevaluacion(BaseModel):
    """Datos para iniciar una autoevaluación; `usuario_id` sale del token."""

    model_config = ConfigDict(extra="forbid")

    empresa_id: UUID
    fecha: date
