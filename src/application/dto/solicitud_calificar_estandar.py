"""DTO de entrada para calificar un estándar mínimo."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SolicitudCalificarEstandar(BaseModel):
    """Resultado y observaciones; rechaza `puntaje` y otros derivados del cliente."""

    model_config = ConfigDict(extra="forbid")

    resultado: Literal["CUMPLE", "NO_CUMPLE", "NO_APLICA"]
    observaciones: str | None = None
