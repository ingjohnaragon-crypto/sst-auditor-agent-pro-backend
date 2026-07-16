"""Pruebas de integración de la fábrica `requerir_roles`."""

from collections.abc import Iterator

import pytest
from fastapi import Depends
from httpx import AsyncClient
from src.domain.models.usuario import RolUsuario, Usuario
from src.main import app
from src.presentation.dependencies.autenticacion import requerir_roles

from tests.integration.conftest import UsuariosSemilla

RUTA_SOLO_ADMIN = "/api/v1/_test/solo-admin"


@pytest.fixture(autouse=True)
def ruta_solo_admin() -> Iterator[None]:
    """Monta y desmonta una ruta auxiliar protegida solo durante estas pruebas."""

    async def endpoint_solo_admin(
        _usuario: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
    ) -> dict[str, bool]:
        return {"autorizado": True}

    app.add_api_route(
        RUTA_SOLO_ADMIN,
        endpoint_solo_admin,
        methods=["GET"],
        include_in_schema=False,
    )
    yield
    app.router.routes = [
        ruta for ruta in app.router.routes if getattr(ruta, "path", None) != RUTA_SOLO_ADMIN
    ]


def _assert_respuesta_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo
    assert isinstance(body["mensaje"], str)


async def _tokens_de(cliente: AsyncClient, correo: str, contrasena: str) -> dict[str, object]:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": correo, "contrasena": contrasena},
    )
    assert respuesta.status_code == 200
    return respuesta.json()


async def test_should_responder_200_when_rol_administrador(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _tokens_de(
        cliente_async, usuarios_semilla.correo_admin, usuarios_semilla.contrasena
    )

    respuesta = await cliente_async.get(
        RUTA_SOLO_ADMIN,
        headers={"Authorization": f"Bearer {tokens['token_acceso']}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"autorizado": True}


async def test_should_responder_403_when_rol_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    tokens = await _tokens_de(
        cliente_async, usuarios_semilla.correo_consulta, usuarios_semilla.contrasena
    )

    respuesta = await cliente_async.get(
        RUTA_SOLO_ADMIN,
        headers={"Authorization": f"Bearer {tokens['token_acceso']}"},
    )

    assert respuesta.status_code == 403
    _assert_respuesta_error(respuesta.json(), "PERMISOS_INSUFICIENTES")
