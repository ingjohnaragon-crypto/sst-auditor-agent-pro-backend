"""DTO de salida de una calificación de estándar mínimo."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RespuestaCalificacionEstandar(BaseModel):
    """Calificación derivada (el puntaje nunca proviene del cliente)."""

    estandar_id: UUID
    resultado: str
    puntaje: Decimal
    observaciones: str | None = None
