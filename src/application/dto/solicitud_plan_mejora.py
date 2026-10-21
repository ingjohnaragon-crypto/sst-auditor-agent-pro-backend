"""DTOs de entrada del plan de mejora."""

from pydantic import BaseModel, ConfigDict, Field


class SolicitudActividadCronograma(BaseModel):
    """Actividad del cronograma. La validez de negocio la decide el dominio."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str
    responsable: str
    indicador: str
    meses: list[int]


class SolicitudAbrirPlanMejora(BaseModel):
    """Alta del plan. La empresa y la autoevaluación no viajan en el cuerpo."""

    model_config = ConfigDict(extra="forbid")

    actividades: list[SolicitudActividadCronograma] = Field(default_factory=list)
