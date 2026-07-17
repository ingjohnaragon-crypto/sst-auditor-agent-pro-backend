"""Pruebas del seed idempotente de estándares mínimos Res. 312."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from scripts.sembrar_estandares_minimos import (
    cargar_items_fixture,
    sembrar_estandares_minimos,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM

FIXTURE_MINIMO = Path(__file__).resolve().parents[2] / "fixtures" / "estandares_minimos_minimo.json"


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


async def test_should_insertar_estandares_when_tabla_vacia(sesion: AsyncSession) -> None:
    creados, omitidos = await sembrar_estandares_minimos(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()

    assert creados == 2
    assert omitidos == 0
    total = (await sesion.execute(select(func.count()).select_from(EstandarMinimoORM))).scalar_one()
    assert total == 2


async def test_should_ser_idempotente_when_se_ejecuta_dos_veces(
    sesion: AsyncSession,
) -> None:
    await sembrar_estandares_minimos(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()
    creados, omitidos = await sembrar_estandares_minimos(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()

    assert creados == 0
    assert omitidos == 2
    total = (await sesion.execute(select(func.count()).select_from(EstandarMinimoORM))).scalar_one()
    assert total == 2


def test_should_fallar_when_fixture_ausente_o_invalido(tmp_path: Path) -> None:
    ruta = tmp_path / "no_existe.json"
    with pytest.raises(RuntimeError, match="No se encontró el fixture"):
        cargar_items_fixture(ruta)

    invalido = tmp_path / "malo.json"
    invalido.write_text("{", encoding="utf-8")
    with pytest.raises(RuntimeError, match="inválido"):
        cargar_items_fixture(invalido)
