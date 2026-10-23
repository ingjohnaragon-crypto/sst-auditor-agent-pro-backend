"""El repositorio no duplica un estándar y el plan borra el borrador en cascada."""

from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
import src.infrastructure.database.modelos  # noqa: F401 — registra las tablas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.accion_mejora import AccionMejora
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.accion_mejora_orm import AccionMejoraORM
from src.infrastructure.repositories.repositorio_accion_mejora_sqlalchemy import (
    RepositorioAccionMejoraSQLAlchemy,
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


def test_should_declarar_borrado_en_cascada_del_plan() -> None:
    claves = list(AccionMejoraORM.plan_mejoramiento_id.foreign_keys)
    nombres = {indice.name for indice in AccionMejoraORM.__table__.indexes}
    assert claves[0].ondelete == "CASCADE"
    assert "ix_acciones_mejora_plan_id" in nombres


async def test_should_devolver_la_existente_when_el_estandar_ya_esta(
    sesion: AsyncSession,
) -> None:
    estandar = EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral="1.1.1",
        descripcion="Ítem",
        valor_porcentual=Decimal("1"),
    )
    repositorio = RepositorioAccionMejoraSQLAlchemy(sesion)
    plan_id = uuid4()
    primera = await repositorio.guardar(AccionMejora.crear(plan_id, estandar))
    fila = await sesion.get(AccionMejoraORM, primera.id)
    assert fila is not None
    fila.responsable_sugerido = "Ana"
    await sesion.flush()

    guardada = await repositorio.guardar(AccionMejora.crear(plan_id, estandar))
    filas = await repositorio.listar_por_plan(plan_id)

    assert guardada.id == primera.id
    assert guardada.responsable_sugerido == "Ana"
    assert len(filas) == 1
