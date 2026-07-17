"""DTO de salida de un ítem del catálogo de estándares mínimos."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RespuestaEstandarMinimo(BaseModel):
    """Ítem del catálogo Res. 0312."""

    id: UUID
    ciclo_phva: str
    numeral: str
    descripcion: str
    valor_porcentual: Decimal
