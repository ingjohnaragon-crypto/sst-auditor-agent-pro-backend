"""DTOs de salida con los tokens emitidos."""

from pydantic import BaseModel

TIPO_TOKEN_BEARER = "Bearer"


class RespuestaTokens(BaseModel):
    """Par de tokens emitido al iniciar sesión."""

    token_acceso: str
    token_refresco: str
    tipo_token: str = TIPO_TOKEN_BEARER
    expira_en_segundos: int


class RespuestaTokenAcceso(BaseModel):
    """Nuevo token de acceso emitido al refrescar."""

    token_acceso: str
    tipo_token: str = TIPO_TOKEN_BEARER
    expira_en_segundos: int
