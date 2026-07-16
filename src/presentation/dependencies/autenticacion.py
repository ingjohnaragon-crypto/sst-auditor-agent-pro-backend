"""Dependencias FastAPI de autenticación: wiring de puertos y guardas de autorización."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_autenticacion import ServicioAutenticacion
from src.domain.exceptions.autenticacion import (
    CredencialesInvalidasException,
    PermisosInsuficientesException,
    TokenInvalidoException,
)
from src.domain.models.usuario import RolUsuario, Usuario
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_hash_contrasena import ServicioHashContrasena
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_usuario_sqlalchemy import (
    RepositorioUsuarioSQLAlchemy,
)
from src.infrastructure.security.hash_bcrypt import HashBcrypt
from src.infrastructure.security.tokens_jwt import TIPO_TOKEN_ACCESO, TokensJWT

SEGUNDOS_POR_MINUTO = 60

# auto_error=False para responder con el contrato RespuestaError (401 TOKEN_INVALIDO)
# en lugar del 403 genérico de FastAPI cuando falta la cabecera Authorization.
esquema_bearer = HTTPBearer(auto_error=False)


def obtener_repositorio_usuario(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioUsuario:
    """Ensambla la implementación SQLAlchemy del repositorio de usuarios."""
    return RepositorioUsuarioSQLAlchemy(sesion)


def obtener_servicio_hash() -> ServicioHashContrasena:
    """Ensambla la implementación bcrypt del puerto de hashing."""
    return HashBcrypt()


def obtener_servicio_tokens() -> ServicioTokens:
    """Ensambla la implementación PyJWT del puerto de tokens."""
    return TokensJWT(get_settings())


def obtener_servicio_autenticacion(
    repositorio: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    servicio_hash: ServicioHashContrasena = Depends(obtener_servicio_hash),
    servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
) -> ServicioAutenticacion:
    """Ensambla el servicio de autenticación con sus tres puertos."""
    settings = get_settings()
    return ServicioAutenticacion(
        repositorio=repositorio,
        servicio_hash=servicio_hash,
        servicio_tokens=servicio_tokens,
        expiracion_acceso_segundos=settings.jwt_minutos_expiracion_acceso * SEGUNDOS_POR_MINUTO,
    )


async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    repositorio: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
) -> Usuario:
    """Valida el Bearer token de acceso y devuelve el usuario autenticado."""
    if credenciales is None:
        raise TokenInvalidoException()
    claims = servicio_tokens.decodificar(credenciales.credentials)
    # Un token de refresco nunca es aceptado como Bearer en endpoints protegidos.
    if claims.get("tipo") != TIPO_TOKEN_ACCESO:
        raise TokenInvalidoException()
    try:
        id_usuario = UUID(str(claims.get("sub")))
    except ValueError as error:
        raise TokenInvalidoException() from error
    usuario = await repositorio.buscar_por_id(id_usuario)
    if usuario is None:
        raise TokenInvalidoException()
    if not usuario.activo:
        raise CredencialesInvalidasException()
    return usuario


def requerir_roles(*roles: RolUsuario) -> Callable[..., Awaitable[Usuario]]:
    """Fábrica de dependencias: exige que el rol del usuario esté en la lista permitida."""

    async def dependencia(
        usuario: Usuario = Depends(obtener_usuario_actual),
    ) -> Usuario:
        if usuario.rol not in roles:
            raise PermisosInsuficientesException()
        return usuario

    return dependencia
