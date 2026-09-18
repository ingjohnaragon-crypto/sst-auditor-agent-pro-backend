"""Suite dedicada de integración HTTP para endpoints de empresas."""

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

_PAYLOAD_BASE = {
    "razon_social": "Empresa Dedicada SA",
    "nit": "901555666-7",
    "actividad_economica": "Consultoría",
    "nivel_riesgo_arl": "II",
    "numero_trabajadores": 12,
}


def _assert_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo
    assert isinstance(body["mensaje"], str)


async def test_should_crear_y_obtener_empresa_when_escritor(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)

    creada = await cliente_async.post(
        "/api/v1/empresas",
        headers=headers,
        json=_PAYLOAD_BASE,
    )
    assert creada.status_code == 201
    empresa_id = creada.json()["id"]
    assert creada.json()["nit"] == _PAYLOAD_BASE["nit"]

    listado = await cliente_async.get("/api/v1/empresas", headers=headers)
    assert listado.status_code == 200
    assert any(e["id"] == empresa_id for e in listado.json())

    detalle = await cliente_async.get(f"/api/v1/empresas/{empresa_id}", headers=headers)
    assert detalle.status_code == 200
    assert detalle.json()["razon_social"] == _PAYLOAD_BASE["razon_social"]


async def test_should_responder_409_when_nit_duplicado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    payload = {**_PAYLOAD_BASE, "nit": "901777888-0"}

    primera = await cliente_async.post("/api/v1/empresas", headers=headers, json=payload)
    assert primera.status_code == 201

    duplicada = await cliente_async.post("/api/v1/empresas", headers=headers, json=payload)
    assert duplicada.status_code == 409
    _assert_error(duplicada.json(), "NIT_DUPLICADO")


async def test_should_responder_403_when_consulta_crea_empresa(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    respuesta = await cliente_async.post(
        "/api/v1/empresas",
        headers=bearer(token),
        json={**_PAYLOAD_BASE, "nit": "901999000-1"},
    )
    assert respuesta.status_code == 403
    _assert_error(respuesta.json(), "ACCESO_DENEGADO")


async def test_should_responder_401_when_sin_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.post("/api/v1/empresas", json=_PAYLOAD_BASE)
    assert respuesta.status_code == 401
    _assert_error(respuesta.json(), "TOKEN_INVALIDO")

    listado = await cliente_async.get("/api/v1/empresas")
    assert listado.status_code == 401
    _assert_error(listado.json(), "TOKEN_INVALIDO")


async def test_should_responder_404_when_empresa_inexistente(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(
        f"/api/v1/empresas/{uuid4()}",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    _assert_error(respuesta.json(), "EMPRESA_NO_ENCONTRADA")
