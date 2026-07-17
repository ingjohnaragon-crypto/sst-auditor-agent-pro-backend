"""DTO de salida de una empresa."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RespuestaEmpresa(BaseModel):
    """Empresa persistida con sus timestamps."""

    id: UUID
    razon_social: str
    nit: str
    actividad_economica: str
    nivel_riesgo_arl: str
    numero_trabajadores: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
