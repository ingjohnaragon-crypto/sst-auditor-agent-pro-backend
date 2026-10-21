"""DTOs de respuesta del plan de mejora."""

from uuid import UUID

from pydantic import BaseModel


class RespuestaActividadCronograma(BaseModel):
    """Actividad pública del cronograma."""

    id: UUID
    descripcion: str
    responsable: str
    indicador: str
    meses: list[int]


class RespuestaPlanMejora(BaseModel):
    """Plan público con sus actividades."""

    id: UUID
    empresa_id: UUID
    autoevaluacion_id: UUID
    actividades: list[RespuestaActividadCronograma]
