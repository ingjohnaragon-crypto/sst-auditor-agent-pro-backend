"""Pruebas del seed idempotente de tipos documentales PHVA."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from scripts.sembrar_estandares_minimos import sembrar_estandares_minimos
from scripts.sembrar_tipos_documento_sst import (
    cargar_items_fixture,
    sembrar_tipos_documento_sst,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM
from src.infrastructure.database.modelos.tipo_documento_estandar_orm import (
    TipoDocumentoEstandarORM,
)
from src.infrastructure.database.modelos.tipo_documento_sst_orm import TipoDocumentoSstORM

FIXTURE_OFICIAL = (
    Path(__file__).resolve().parents[3] / "scripts" / "datos" / "tipos_documento_sst_phva.json"
)
FIXTURE_ESTANDARES = (
    Path(__file__).resolve().parents[3] / "scripts" / "datos" / "estandares_minimos_res312.json"
)


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


async def test_should_insertar_diez_tipos_when_tabla_vacia(sesion: AsyncSession) -> None:
    creados, omitidos = await sembrar_tipos_documento_sst(sesion)
    await sesion.commit()

    assert creados == 10
    assert omitidos == 0
    total = (
        await sesion.execute(select(func.count()).select_from(TipoDocumentoSstORM))
    ).scalar_one()
    assert total == 10


async def test_should_ser_idempotente_y_no_tocar_estandares(
    sesion: AsyncSession,
) -> None:
    await sembrar_estandares_minimos(sesion, ruta_fixture=FIXTURE_ESTANDARES)
    await sesion.commit()
    total_estandares = (
        await sesion.execute(select(func.count()).select_from(EstandarMinimoORM))
    ).scalar_one()

    await sembrar_tipos_documento_sst(sesion)
    await sesion.commit()
    creados, omitidos = await sembrar_tipos_documento_sst(sesion)
    await sesion.commit()

    assert creados == 0
    assert omitidos == 10
    total_tipos = (
        await sesion.execute(select(func.count()).select_from(TipoDocumentoSstORM))
    ).scalar_one()
    assert total_tipos == 10
    total_estandares_despues = (
        await sesion.execute(select(func.count()).select_from(EstandarMinimoORM))
    ).scalar_one()
    assert total_estandares_despues == total_estandares
    vinculos = (
        await sesion.execute(select(func.count()).select_from(TipoDocumentoEstandarORM))
    ).scalar_one()
    assert vinculos == 10


def test_should_validar_fixture_oficial() -> None:
    items = cargar_items_fixture(FIXTURE_OFICIAL)
    codigos = [str(item["codigo"]) for item in items]
    assert len(items) == 10
    assert len(set(codigos)) == 10
    assert "POLITICA_SST" in codigos
    assert "PLAN_MEJORA" in codigos
