"""Pruebas de integración de POST /api/v1/auth/login."""

from httpx import AsyncClient

from tests.integration.conftest import UsuariosSemilla


def _assert_respuesta_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo
    assert isinstance(body["mensaje"], str)
    assert "mensaje" in body


async def test_should_devolver_tokens_when_credenciales_validas(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        json={
            "correo": usuarios_semilla.correo_admin,
            "contrasena": usuarios_semilla.contrasena,
        },
    )

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["tipo_token"] == "Bearer"
    assert body["expira_en_segundos"] == 1800
    assert isinstance(body["token_acceso"], str) and body["token_acceso"]
    assert isinstance(body["token_refresco"], str) and body["token_refresco"]
    assert "hash_contrasena" not in body


async def test_should_responder_401_when_correo_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        json={"correo": "nadie@empresa.com", "contrasena": usuarios_semilla.contrasena},
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "CREDENCIALES_INVALIDAS")


async def test_should_responder_401_when_contrasena_incorrecta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        json={"correo": usuarios_semilla.correo_admin, "contrasena": "OtraClave9!"},
    )

    assert respuesta.status_code == 401
    body = respuesta.json()
    _assert_respuesta_error(body, "CREDENCIALES_INVALIDAS")

    # Mismo mensaje genérico que correo inexistente (sin enumeración).
    inexistente = await cliente_async.post(
        "/api/v1/auth/login",
        json={"correo": "nadie@empresa.com", "contrasena": usuarios_semilla.contrasena},
    )
    assert body["mensaje"] == inexistente.json()["mensaje"]


async def test_should_responder_401_when_usuario_inactivo(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        json={
            "correo": usuarios_semilla.correo_inactivo,
            "contrasena": usuarios_semilla.contrasena,
        },
    )

    assert respuesta.status_code == 401
    _assert_respuesta_error(respuesta.json(), "CREDENCIALES_INVALIDAS")


async def test_should_responder_422_when_body_invalido(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        json={"correo": "no-es-correo", "contrasena": "corta"},
    )

    assert respuesta.status_code == 422
    _assert_respuesta_error(respuesta.json(), "ERROR_VALIDACION")
