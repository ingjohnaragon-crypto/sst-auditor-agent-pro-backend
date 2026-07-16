"""Implementación PyJWT del puerto `ServicioTokens` (firma HS256)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from src.domain.exceptions.autenticacion import TokenExpiradoException, TokenInvalidoException
from src.domain.models.usuario import Usuario
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.config.settings import Settings

TIPO_TOKEN_ACCESO = "acceso"
TIPO_TOKEN_REFRESCO = "refresco"
ALGORITMO_JWT = "HS256"


class TokensJWT(ServicioTokens):
    """Emite y valida JWT firmados con el secreto de `Settings` (siempre HS256)."""

    def __init__(self, settings: Settings) -> None:
        self._secreto = settings.jwt_secreto
        self._expiracion_acceso = timedelta(minutes=settings.jwt_minutos_expiracion_acceso)
        self._expiracion_refresco = timedelta(days=settings.jwt_dias_expiracion_refresco)

    def emitir_token_acceso(self, usuario: Usuario) -> str:
        ahora = datetime.now(UTC)
        claims: dict[str, object] = {
            "sub": str(usuario.id),
            "rol": usuario.rol.value,
            "tipo": TIPO_TOKEN_ACCESO,
            "iat": ahora,
            "exp": ahora + self._expiracion_acceso,
            "jti": str(uuid4()),
        }
        return jwt.encode(claims, self._secreto, algorithm=ALGORITMO_JWT)

    def emitir_token_refresco(self, usuario: Usuario) -> str:
        ahora = datetime.now(UTC)
        # Sin claim `rol`: el token de refresco no otorga acceso a recursos.
        claims: dict[str, object] = {
            "sub": str(usuario.id),
            "tipo": TIPO_TOKEN_REFRESCO,
            "iat": ahora,
            "exp": ahora + self._expiracion_refresco,
            "jti": str(uuid4()),
        }
        return jwt.encode(claims, self._secreto, algorithm=ALGORITMO_JWT)

    def decodificar(self, token: str) -> dict[str, object]:
        try:
            # Lista fija a HS256 — previene el ataque de algoritmo `none`.
            claims: dict[str, object] = jwt.decode(token, self._secreto, algorithms=[ALGORITMO_JWT])
        except jwt.ExpiredSignatureError as error:
            raise TokenExpiradoException() from error
        except jwt.InvalidTokenError as error:
            raise TokenInvalidoException() from error
        return claims
