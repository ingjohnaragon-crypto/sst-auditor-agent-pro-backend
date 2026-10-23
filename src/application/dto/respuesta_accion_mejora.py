"""DTO de salida del borrador de acciones de mejora."""

from uuid import UUID

from pydantic import BaseModel


class RespuestaAccionMejora(BaseModel):
    """Acción pública generada desde un incumplimiento."""

    id: UUID
    plan_id: UUID
    estandar_id: UUID
    numeral: str
    descripcion: str
    ciclo_phva: str
    responsable_sugerido: str | None
