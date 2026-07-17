"""DTO de salida de una autoevaluación."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.dto.respuesta_calificacion_estandar import (
    RespuestaCalificacionEstandar,
)


class RespuestaAutoevaluacion(BaseModel):
    """Autoevaluación con calificaciones embebidas (vacías en el listado histórico)."""

    id: UUID
    empresa_id: UUID
    usuario_id: UUID
    fecha: date
    puntaje_total: Decimal | None
    requiere_plan_mejora: bool
    calificaciones: list[RespuestaCalificacionEstandar] = Field(default_factory=list)
    fecha_creacion: datetime
    fecha_actualizacion: datetime
