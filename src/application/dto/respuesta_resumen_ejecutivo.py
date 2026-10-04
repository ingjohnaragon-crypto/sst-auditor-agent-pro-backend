"""DTO de lectura del resumen ejecutivo de una empresa."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ResultadoIrrenunciable = Literal["CUMPLE", "NO_CUMPLE", "NO_APLICA", "SIN_CALIFICAR"]


class DistribucionRiesgos(BaseModel):
    """Conteos por interpretación NR ya persistida. Las claves JSON son I–IV."""

    model_config = ConfigDict(populate_by_name=True)

    nivel_i: int = Field(alias="I", ge=0)
    nivel_ii: int = Field(alias="II", ge=0)
    nivel_iii: int = Field(alias="III", ge=0)
    nivel_iv: int = Field(alias="IV", ge=0)


class IrrenunciableResumen(BaseModel):
    """Estado de un estándar irrenunciable en la última autoevaluación."""

    numeral: str
    descripcion: str
    resultado: ResultadoIrrenunciable


class RespuestaResumenEjecutivo(BaseModel):
    """Resumen de solo lectura para el inicio. No recalcula 0312 ni la GTC 45."""

    model_config = ConfigDict(populate_by_name=True)

    empresa_id: UUID
    cantidad_autoevaluaciones: int = Field(ge=0)
    autoevaluacion_id: UUID | None
    requiere_plan_mejora: bool
    riesgos_nivel_i: int = Field(ge=0)
    riesgos_nivel_ii: int = Field(ge=0)
    distribucion_riesgos: DistribucionRiesgos
    irrenunciables: list[IrrenunciableResumen]
