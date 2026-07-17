"""Pruebas del orquestador `sembrar_datos`."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from scripts.sembrar_datos import hay_credenciales_admin, sembrar_datos


def test_should_detectar_credenciales_admin_when_completas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_INICIAL_CORREO", "a@b.com")
    monkeypatch.setenv("ADMIN_INICIAL_CONTRASENA", "secreto12")
    monkeypatch.setenv("ADMIN_INICIAL_NOMBRE", "Admin")
    assert hay_credenciales_admin() is True


def test_should_omitir_admin_when_faltan_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nombre in (
        "ADMIN_INICIAL_CORREO",
        "ADMIN_INICIAL_CONTRASENA",
        "ADMIN_INICIAL_NOMBRE",
    ):
        monkeypatch.delenv(nombre, raising=False)
    assert hay_credenciales_admin() is False


@pytest.mark.asyncio
async def test_should_llamar_seeds_en_orden_when_sembrar_datos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_INICIAL_CORREO", raising=False)
    orden: list[str] = []

    async def mock_estandares(sesion: object, **_: object) -> tuple[int, int]:
        orden.append("estandares")
        return 1, 0

    async def mock_catalogos(sesion: object, **_: object) -> tuple[int, int]:
        orden.append("catalogos")
        return 1, 0

    sesion = AsyncMock()
    sesion.commit = AsyncMock()
    fabrica = MagicMock()
    fabrica.return_value.__aenter__ = AsyncMock(return_value=sesion)
    fabrica.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("scripts.sembrar_datos.obtener_fabrica_sesiones", return_value=fabrica),
        patch(
            "scripts.sembrar_datos.sembrar_estandares_minimos",
            side_effect=mock_estandares,
        ),
        patch(
            "scripts.sembrar_datos.sembrar_catalogos_gtc45",
            side_effect=mock_catalogos,
        ),
    ):
        await sembrar_datos()

    assert orden == ["estandares", "catalogos"]
    sesion.commit.assert_awaited_once()
