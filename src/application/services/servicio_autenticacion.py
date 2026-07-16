"""Casos de uso de autenticación — orquesta puertos del dominio, sin infraestructura."""

import logging
from uuid import UUID

from src.application.dto.respuesta_tokens import RespuestaTokenAcceso, RespuestaTokens
from src.application.dto.respuesta_usuario import RespuestaUsuario
from src.application.dto.solicitud_login import SolicitudLogin
from src.application.dto.solicitud_refresh import SolicitudRefresh
from src.application.mappers.mapper_usuario import MapperUsuario
from src.domain.exceptions.autenticacion import (
    CredencialesInvalidasException,
    TokenInvalidoException,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_hash_contrasena import ServicioHashContrasena
from src.domain.repositories.servicio_tokens import ServicioTokens

logger = logging.getLogger(__name__)

TIPO_CLAIM_REFRESCO = "refresco"

# Hash bcrypt (costo 12) de una cadena aleatoria descartada. Cuando el correo no
# existe se verifica contra este señuelo para que el tiempo de respuesta sea el
# mismo que con un usuario real (mitigación de enumeración por timing).
HASH_SENUELO = "$2b$12$cbysOYoVmxYj3vdZ19aPauvxjlpEWHL9m6PurS7a/KxY4IBlz0jAa"


class ServicioAutenticacion:
    """Casos de uso: iniciar sesión, refrescar token y obtener el perfil propio."""

    def __init__(
        self,
        repositorio: RepositorioUsuario,
        servicio_hash: ServicioHashContrasena,
        servicio_tokens: ServicioTokens,
        expiracion_acceso_segundos: int,
    ) -> None:
        self._repositorio = repositorio
        self._servicio_hash = servicio_hash
        self._servicio_tokens = servicio_tokens
        self._expiracion_acceso_segundos = expiracion_acceso_segundos

    async def iniciar_sesion(self, dto: SolicitudLogin) -> RespuestaTokens:
        """Valida credenciales y emite el par de tokens (acceso + refresco)."""
        correo = dto.correo.lower()
        usuario = await self._repositorio.buscar_por_correo(correo)
        # La verificación bcrypt se ejecuta siempre (señuelo si no hay usuario).
        hash_a_verificar = usuario.hash_contrasena if usuario is not None else HASH_SENUELO
        contrasena_valida = await self._servicio_hash.verificar(
            dto.contrasena.get_secret_value(), hash_a_verificar
        )
        if usuario is None or not contrasena_valida or not usuario.activo:
            logger.warning("Inicio de sesión fallido para el correo %s", correo)
            raise CredencialesInvalidasException()
        logger.info("Inicio de sesión exitoso para el correo %s", correo)
        return RespuestaTokens(
            token_acceso=self._servicio_tokens.emitir_token_acceso(usuario),
            token_refresco=self._servicio_tokens.emitir_token_refresco(usuario),
            expira_en_segundos=self._expiracion_acceso_segundos,
        )

    async def refrescar_token(self, dto: SolicitudRefresh) -> RespuestaTokenAcceso:
        """Emite un nuevo token de acceso a partir de un token de refresco válido."""
        claims = self._servicio_tokens.decodificar(dto.token_refresco)
        if claims.get("tipo") != TIPO_CLAIM_REFRESCO:
            raise TokenInvalidoException()
        usuario = await self._repositorio.buscar_por_id(self._extraer_sub(claims))
        if usuario is None or not usuario.activo:
            raise CredencialesInvalidasException()
        return RespuestaTokenAcceso(
            token_acceso=self._servicio_tokens.emitir_token_acceso(usuario),
            expira_en_segundos=self._expiracion_acceso_segundos,
        )

    async def obtener_perfil(self, id: UUID) -> RespuestaUsuario:
        """Devuelve el perfil del usuario autenticado (sin credenciales)."""
        usuario = await self._repositorio.buscar_por_id(id)
        if usuario is None:
            raise TokenInvalidoException()
        return MapperUsuario.a_respuesta(usuario)

    @staticmethod
    def _extraer_sub(claims: dict[str, object]) -> UUID:
        try:
            return UUID(str(claims.get("sub")))
        except ValueError as error:
            raise TokenInvalidoException() from error
