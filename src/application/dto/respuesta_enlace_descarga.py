"""DTO del enlace temporal de descarga."""

from pydantic import BaseModel


class RespuestaEnlaceDescarga(BaseModel):
    """URL relativa y segundos de vigencia. El token no se repite fuera de la URL."""

    url: str
    expira_en_segundos: int
