"""DTO Pydantic que formaliza el contrato único de error del API."""

from pydantic import BaseModel


class RespuestaError(BaseModel):
    """Contrato único de toda respuesta de error del API (4xx y 5xx)."""

    exito: bool = False
    codigo: str
    mensaje: str
    detalle: list[dict[str, object]] | dict[str, object] | None = None
