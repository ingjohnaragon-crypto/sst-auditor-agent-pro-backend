"""Pruebas de integración de POST /api/v1/auth/refresh."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from httpx import AsyncClient
from src.infrastructure.config.settings import get_settings

from tests.integration.conftest import UsuariosSemilla


def _assert_respuesta_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo
    assert isinstance(body["mensaje"], str)


async def _login(cliente: AsyncClient, usuarios: UsuariosSemilla) -> dict[str, object]:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": usuarios.correo_admin, "contrasena": usuarios.contrasena},
    )
    assert respuesta.status_code == 200
    return respuesta.json()


async def test_should_emitir_nuevo_token_acceso_when_refresh_valido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)

    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"token_refresco": tokens["token_refresco"]},
    )

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["tipo_token"] == "Bearer"
    assert body["expira_en_segundos"] == 1800
    assert isinstance(body["token_acceso"], str) and body["token_acceso"]
    assert "token_refresco" not in body


async def test_should_responder_401_when_refresh_recibe_token_de_acceso(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)

    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"token_refresco": tokens["token_acceso"]},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_INVALIDO")


async def test_should_responder_401_when_token_refresco_expirado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)
    settings = get_settings()
    claims = jwt.decode(
        str(tokens["token_refresco"]),
        settings.jwt_secreto,
        algorithms=["HS256"],
    )
    ahora = datetime.now(UTC)
    claims["iat"] = ahora - timedelta(days=10)
    claims["exp"] = ahora - timedelta(days=1)
    claims["jti"] = str(uuid4())
    token_expirado = jwt.encode(claims, settings.jwt_secreto, algorithm="HS256")

    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"token_refresco": token_expirado},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_EXPIRADO")


async def test_should_responder_401_when_token_mal_firmado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)
    settings = get_settings()
    claims = jwt.decode(
        str(tokens["token_refresco"]),
        settings.jwt_secreto,
        algorithms=["HS256"],
    )
    token_ajeno = jwt.encode(
        claims,
        "secreto-falso-distinto-de-32-caracteres!!!!",
        algorithm="HS256",
    )

    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"token_refresco": token_ajeno},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_INVALIDO")
