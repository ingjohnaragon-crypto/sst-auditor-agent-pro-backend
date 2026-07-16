"""Pruebas de integración de GET /api/v1/auth/yo."""

from httpx import AsyncClient

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


async def test_should_devolver_perfil_when_bearer_valido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)

    respuesta = await cliente_async.get(
        "/api/v1/auth/yo",
        headers={"Authorization": f"Bearer {tokens['token_acceso']}"},
    )

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["correo"] == usuarios_semilla.correo_admin
    assert body["nombre_completo"] == "Admin Prueba"
    assert body["rol"] == "ADMINISTRADOR"
    assert "id" in body
    assert "hash_contrasena" not in body


async def test_should_responder_401_when_sin_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.get("/api/v1/auth/yo")

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_INVALIDO")


async def test_should_responder_401_when_token_corrupto(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.get(
        "/api/v1/auth/yo",
        headers={"Authorization": "Bearer token.totalmente.corrupto"},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_INVALIDO")


async def test_should_responder_401_when_token_refresco_como_bearer(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _login(cliente_async, usuarios_semilla)

    respuesta = await cliente_async.get(
        "/api/v1/auth/yo",
        headers={"Authorization": f"Bearer {tokens['token_refresco']}"},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "TOKEN_INVALIDO")
