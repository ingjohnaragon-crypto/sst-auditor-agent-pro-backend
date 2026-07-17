"""DTO de entrada para crear una empresa."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SolicitudCrearEmpresa(BaseModel):
    """Datos para registrar una empresa evaluada bajo el SG-SST."""

    model_config = ConfigDict(extra="forbid")

    razon_social: str = Field(min_length=1)
    nit: str = Field(min_length=1)
    actividad_economica: str = Field(min_length=1)
    nivel_riesgo_arl: Literal["I", "II", "III", "IV", "V"]
    numero_trabajadores: int = Field(gt=0)
