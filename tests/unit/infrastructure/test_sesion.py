"""Pruebas de la fábrica de sesiones async y la dependencia `obtener_sesion`."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.sesion import (
    obtener_fabrica_sesiones,
    obtener_motor,
    obtener_sesion,
)


def _limpiar_caches() -> None:
    """Restaura el estado global de las cachés lru_cache de settings y sesión."""
    get_settings.cache_clear()
    obtener_motor.cache_clear()
    obtener_fabrica_sesiones.cache_clear()


@pytest.fixture
def caches_limpias() -> Iterator[None]:
    """Limpia las cachés antes y después para no contaminar el resto de la suite."""
    _limpiar_caches()
    yield
    _limpiar_caches()


def test_should_crear_motor_con_parametros_de_pool_when_settings_configurados(
    monkeypatch: pytest.MonkeyPatch, caches_limpias: None
) -> None:
    """Con una URL PostgreSQL, el motor recibe la configuración completa del pool."""
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql+asyncpg://u:p@localhost/db")
    with patch("src.infrastructure.database.sesion.create_async_engine") as motor_falso:
        motor_falso.return_value = MagicMock(spec=AsyncEngine)

        obtener_motor()

        motor_falso.assert_called_once_with(
            "postgresql+asyncpg://u:p@localhost/db",
            echo=False,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=10,
        )


def test_should_omitir_dimensionamiento_de_pool_when_url_es_sqlite(
    caches_limpias: None,
) -> None:
    """Con SQLite (StaticPool) no se pasan pool_size/max_overflow, pero sí el resto."""
    with patch("src.infrastructure.database.sesion.create_async_engine") as motor_falso:
        motor_falso.return_value = MagicMock(spec=AsyncEngine)

        obtener_motor()

        argumentos = motor_falso.call_args.kwargs
        assert "pool_size" not in argumentos
        assert "max_overflow" not in argumentos
        assert argumentos["pool_pre_ping"] is True
        assert argumentos["pool_recycle"] == 1800
        assert argumentos["echo"] is False


def test_should_cachear_el_motor_y_la_fabrica() -> None:
    assert obtener_motor() is obtener_motor()
    assert obtener_fabrica_sesiones() is obtener_fabrica_sesiones()
    assert isinstance(obtener_motor(), AsyncEngine)


async def test_should_entregar_sesion_async_y_confirmar_al_exito() -> None:
    generador = obtener_sesion()

    sesion = await anext(generador)
    assert isinstance(sesion, AsyncSession)
    resultado = await sesion.execute(text("SELECT 1"))
    assert resultado.scalar_one() == 1

    with pytest.raises(StopAsyncIteration):
        await anext(generador)


async def test_should_hacer_rollback_when_la_peticion_falla() -> None:
    generador = obtener_sesion()
    await anext(generador)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        await generador.athrow(RuntimeError("fallo simulado"))
