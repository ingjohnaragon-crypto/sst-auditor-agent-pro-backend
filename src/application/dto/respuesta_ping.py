"""DTO Pydantic de la respuesta del endpoint de conectividad ping/pong."""

from pydantic import BaseModel, Field


class RespuestaPing(BaseModel):
    """Respuesta del endpoint de conectividad ping/pong."""

    mensaje: str = Field(examples=["pong"])
