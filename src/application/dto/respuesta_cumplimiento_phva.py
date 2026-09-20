"""DTO de respuesta del cumplimiento PHVA por perfil Res. 0312."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RespuestaCumplimientoFasePHVA(BaseModel):
    """Cumplimiento de una fase del ciclo PHVA."""

    ciclo_phva: str
    peso_maximo: Decimal
    puntaje_obtenido: Decimal
    porcentaje_cumplimiento: Decimal
    brecha: Decimal


class RespuestaCumplimientoPHVA(BaseModel):
    """Resumen de cumplimiento global y por fase para una autoevaluación."""

    autoevaluacion_id: UUID
    empresa_id: UUID
    perfil: str
    puntaje_total: Decimal
    umbral_plan_mejora: Decimal
    requiere_plan_mejora: bool
    finalizada: bool
    fases: list[RespuestaCumplimientoFasePHVA] = Field(default_factory=list)
