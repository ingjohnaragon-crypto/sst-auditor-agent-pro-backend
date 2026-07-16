"""Pruebas de la fábrica de sesiones async y la dependencia `obtener_sesion`."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from src.infrastructure.database.sesion import (
    obtener_fabrica_sesiones,
    obtener_motor,
    obtener_sesion,
)


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
