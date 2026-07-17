"""Pruebas del seed idempotente de catálogos GTC 45."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from scripts.sembrar_catalogos_gtc45 import (
    cargar_items_fixture,
    sembrar_catalogos_gtc45,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.catalogo_referencia_orm import CatalogoReferenciaORM

FIXTURE_MINIMO = Path(__file__).resolve().parents[2] / "fixtures" / "catalogos_gtc45_minimo.json"
FIXTURE_OFICIAL = Path(__file__).resolve().parents[3] / "scripts" / "datos" / "catalogos_gtc45.json"


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


async def test_should_incluir_nd_bajo_cero_when_sembrar_gtc45(
    sesion: AsyncSession,
) -> None:
    await sembrar_catalogos_gtc45(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()

    fila = (
        await sesion.execute(
            select(CatalogoReferenciaORM).where(
                CatalogoReferenciaORM.tipo == "NIVEL_DEFICIENCIA",
                CatalogoReferenciaORM.codigo == "BAJO",
            )
        )
    ).scalar_one()
    assert fila.valor_numerico == 0


async def test_should_sembrar_todos_los_tipos_de_control_when_catalogo_gtc45(
    sesion: AsyncSession,
) -> None:
    await sembrar_catalogos_gtc45(sesion, ruta_fixture=FIXTURE_OFICIAL)
    await sesion.commit()

    controles = (
        (
            await sesion.execute(
                select(CatalogoReferenciaORM.codigo).where(
                    CatalogoReferenciaORM.tipo == "TIPO_CONTROL"
                )
            )
        )
        .scalars()
        .all()
    )
    assert set(controles) == {
        "ELIMINACION",
        "SUSTITUCION",
        "INGENIERIA",
        "ADMINISTRATIVO",
        "EPP",
    }


async def test_should_ser_idempotente_when_se_ejecuta_dos_veces(
    sesion: AsyncSession,
) -> None:
    await sembrar_catalogos_gtc45(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()
    creados, omitidos = await sembrar_catalogos_gtc45(sesion, ruta_fixture=FIXTURE_MINIMO)
    await sesion.commit()

    assert creados == 0
    assert omitidos == 6
    total = (
        await sesion.execute(select(func.count()).select_from(CatalogoReferenciaORM))
    ).scalar_one()
    assert total == 6


def test_should_fallar_when_fixture_ausente() -> None:
    with pytest.raises(RuntimeError, match="No se encontró el fixture"):
        cargar_items_fixture(Path("no/existe.json"))
