"""DTO de entrada de la renovación del token de acceso."""

from pydantic import BaseModel


class SolicitudRefresh(BaseModel):
    """Token de refresco a partir del cual se emite un nuevo token de acceso."""

    token_refresco: str
