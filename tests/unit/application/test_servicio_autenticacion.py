"""Pruebas unitarias de `ServicioAutenticacion` — puertos mockeados, sin infraestructura."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.application.dto.solicitud_login import SolicitudLogin
from src.application.dto.solicitud_refresh import SolicitudRefresh
from src.application.services.servicio_autenticacion import (
    HASH_SENUELO,
    ServicioAutenticacion,
)
from src.domain.exceptions.autenticacion import (
    CredencialesInvalidasException,
    TokenExpiradoException,
    TokenInvalidoException,
)
from src.domain.models.usuario import RolUsuario, Usuario

EXPIRACION_ACCESO_SEGUNDOS = 1800
CONTRASENA = "Contrasena123"


def construir_usuario(activo: bool = True) -> Usuario:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="$2b$12$hashalmacenado",
        rol=RolUsuario.AUDITOR_SST,
    )
    usuario.id = uuid4()
    usuario.activo = activo
    return usuario


def construir_servicio(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> ServicioAutenticacion:
    return ServicioAutenticacion(
        repositorio=repositorio,
        servicio_hash=servicio_hash,
        servicio_tokens=servicio_tokens,
        expiracion_acceso_segundos=EXPIRACION_ACCESO_SEGUNDOS,
    )


@pytest.fixture
def repositorio() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def servicio_hash() -> AsyncMock:
    mock = AsyncMock()
    mock.verificar.return_value = True
    return mock


@pytest.fixture
def servicio_tokens() -> MagicMock:
    mock = MagicMock()
    mock.emitir_token_acceso.return_value = "token-de-acceso"
    mock.emitir_token_refresco.return_value = "token-de-refresco"
    return mock


async def test_should_devolver_tokens_when_credenciales_validas(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    usuario = construir_usuario()
    repositorio.buscar_por_correo.return_value = usuario
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)
    dto = SolicitudLogin(correo="ana@empresa.com", contrasena=CONTRASENA)

    respuesta = await servicio.iniciar_sesion(dto)

    assert respuesta.token_acceso == "token-de-acceso"
    assert respuesta.token_refresco == "token-de-refresco"
    assert respuesta.tipo_token == "Bearer"
    assert respuesta.expira_en_segundos == EXPIRACION_ACCESO_SEGUNDOS
    servicio_hash.verificar.assert_awaited_once_with(CONTRASENA, usuario.hash_contrasena)


async def test_should_lanzar_credenciales_invalidas_when_correo_no_existe(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    repositorio.buscar_por_correo.return_value = None
    servicio_hash.verificar.return_value = False
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)
    dto = SolicitudLogin(correo="nadie@empresa.com", contrasena=CONTRASENA)

    with pytest.raises(CredencialesInvalidasException):
        await servicio.iniciar_sesion(dto)

    # La verificación bcrypt se ejecuta igualmente contra el hash señuelo
    # (mitigación de enumeración de usuarios por tiempo de respuesta).
    servicio_hash.verificar.assert_awaited_once_with(CONTRASENA, HASH_SENUELO)


async def test_should_lanzar_credenciales_invalidas_when_contrasena_incorrecta(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    repositorio.buscar_por_correo.return_value = construir_usuario()
    servicio_hash.verificar.return_value = False
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)
    dto = SolicitudLogin(correo="ana@empresa.com", contrasena="ContrasenaMala1")

    with pytest.raises(CredencialesInvalidasException):
        await servicio.iniciar_sesion(dto)


async def test_should_lanzar_credenciales_invalidas_when_usuario_inactivo(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    repositorio.buscar_por_correo.return_value = construir_usuario(activo=False)
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)
    dto = SolicitudLogin(correo="ana@empresa.com", contrasena=CONTRASENA)

    with pytest.raises(CredencialesInvalidasException):
        await servicio.iniciar_sesion(dto)


async def test_should_usar_mismo_mensaje_when_correo_o_contrasena_fallan(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    repositorio.buscar_por_correo.return_value = None
    servicio_hash.verificar.return_value = False
    with pytest.raises(CredencialesInvalidasException) as error_correo:
        await servicio.iniciar_sesion(
            SolicitudLogin(correo="nadie@empresa.com", contrasena=CONTRASENA)
        )

    repositorio.buscar_por_correo.return_value = construir_usuario()
    with pytest.raises(CredencialesInvalidasException) as error_contrasena:
        await servicio.iniciar_sesion(
            SolicitudLogin(correo="ana@empresa.com", contrasena=CONTRASENA)
        )

    assert error_correo.value.message == error_contrasena.value.message


async def test_should_emitir_nuevo_token_acceso_when_refresh_valido(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    usuario = construir_usuario()
    repositorio.buscar_por_id.return_value = usuario
    servicio_tokens.decodificar.return_value = {"tipo": "refresco", "sub": str(usuario.id)}
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    respuesta = await servicio.refrescar_token(SolicitudRefresh(token_refresco="token-valido"))

    assert respuesta.token_acceso == "token-de-acceso"
    assert respuesta.expira_en_segundos == EXPIRACION_ACCESO_SEGUNDOS
    repositorio.buscar_por_id.assert_awaited_once_with(usuario.id)


async def test_should_lanzar_token_invalido_when_refresh_recibe_token_de_acceso(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    servicio_tokens.decodificar.return_value = {"tipo": "acceso", "sub": str(uuid4())}
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    with pytest.raises(TokenInvalidoException):
        await servicio.refrescar_token(SolicitudRefresh(token_refresco="token-de-acceso"))


async def test_should_lanzar_token_expirado_when_token_vencido(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    servicio_tokens.decodificar.side_effect = TokenExpiradoException()
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    with pytest.raises(TokenExpiradoException):
        await servicio.refrescar_token(SolicitudRefresh(token_refresco="token-vencido"))


async def test_should_lanzar_token_invalido_when_sub_no_es_uuid(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    servicio_tokens.decodificar.return_value = {"tipo": "refresco", "sub": "no-es-uuid"}
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    with pytest.raises(TokenInvalidoException):
        await servicio.refrescar_token(SolicitudRefresh(token_refresco="token-corrupto"))


async def test_should_lanzar_credenciales_invalidas_when_refresh_de_usuario_inactivo(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    usuario = construir_usuario(activo=False)
    repositorio.buscar_por_id.return_value = usuario
    servicio_tokens.decodificar.return_value = {"tipo": "refresco", "sub": str(usuario.id)}
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    with pytest.raises(CredencialesInvalidasException):
        await servicio.refrescar_token(SolicitudRefresh(token_refresco="token-valido"))


async def test_should_devolver_perfil_when_usuario_existe(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    usuario = construir_usuario()
    repositorio.buscar_por_id.return_value = usuario
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)
    assert usuario.id is not None

    respuesta = await servicio.obtener_perfil(usuario.id)

    assert respuesta.id == usuario.id
    assert respuesta.correo == usuario.correo
    assert respuesta.rol == usuario.rol.value
    assert not hasattr(respuesta, "hash_contrasena")


async def test_should_lanzar_token_invalido_when_perfil_de_usuario_inexistente(
    repositorio: AsyncMock, servicio_hash: AsyncMock, servicio_tokens: MagicMock
) -> None:
    repositorio.buscar_por_id.return_value = None
    servicio = construir_servicio(repositorio, servicio_hash, servicio_tokens)

    with pytest.raises(TokenInvalidoException):
        await servicio.obtener_perfil(uuid4())
