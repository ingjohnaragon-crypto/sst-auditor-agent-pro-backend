"""Suite dedicada de integración HTTP para estándares mínimos."""

from httpx import AsyncClient

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token


def _assert_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo
    assert isinstance(body["mensaje"], str)


async def test_should_listar_estandares_when_autenticado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(
        "/api/v1/estandares-minimos",
        headers=bearer(token),
    )
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 3


async def test_should_filtrar_estandares_por_ciclo_phva(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)

    planear = await cliente_async.get(
        "/api/v1/estandares-minimos?ciclo_phva=PLANEAR",
        headers=headers,
    )
    assert planear.status_code == 200
    assert all(e["ciclo_phva"] == "PLANEAR" for e in planear.json())
    assert len(planear.json()) == 2


async def test_should_responder_422_when_ciclo_phva_invalido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(
        "/api/v1/estandares-minimos?ciclo_phva=OTRO",
        headers=bearer(token),
    )
    assert respuesta.status_code == 422
    body = respuesta.json()
    assert body["exito"] is False
    assert isinstance(body["mensaje"], str)


async def test_should_responder_401_when_sin_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.get("/api/v1/estandares-minimos")
    assert respuesta.status_code == 401
    _assert_error(respuesta.json(), "TOKEN_INVALIDO")
