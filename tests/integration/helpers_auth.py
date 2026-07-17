"""Helpers compartidos de autenticación para pruebas de integración."""

from httpx import AsyncClient

from tests.integration.conftest import UsuariosSemilla


async def obtener_token(
    cliente: AsyncClient,
    usuarios: UsuariosSemilla,
    *,
    correo: str | None = None,
) -> str:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": correo or usuarios.correo_admin,
            "contrasena": usuarios.contrasena,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    return str(respuesta.json()["token_acceso"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
