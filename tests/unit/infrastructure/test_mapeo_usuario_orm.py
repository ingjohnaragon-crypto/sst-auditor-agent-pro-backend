"""Pruebas del repositorio SQLAlchemy: mapeo ORM ↔ dominio sin pérdida."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.database.base import Base
from src.infrastructure.repositories.repositorio_usuario_sqlalchemy import (
    RepositorioUsuarioSQLAlchemy,
)


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    # `create_all` está permitido únicamente en tests; el esquema real lo crea Alembic.
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


def construir_usuario(correo: str = "ana@empresa.com") -> Usuario:
    return Usuario.crear(
        nombre_completo="Ana Auditora",
        correo=correo,
        hash_contrasena="$2b$12$hashalmacenado",
        rol=RolUsuario.AUDITOR_SST,
    )


async def test_should_guardar_y_devolver_entidad_de_dominio(sesion: AsyncSession) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)

    guardado = await repositorio.guardar(construir_usuario())

    assert isinstance(guardado, Usuario)
    assert guardado.id is not None
    assert guardado.fecha_creacion is not None
    assert guardado.fecha_actualizacion is not None


async def test_should_mapear_ida_y_vuelta_sin_perdida(sesion: AsyncSession) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)
    guardado = await repositorio.guardar(construir_usuario())
    assert guardado.id is not None

    recuperado = await repositorio.buscar_por_id(guardado.id)

    assert recuperado is not None
    assert recuperado.id == guardado.id
    assert recuperado.nombre_completo == "Ana Auditora"
    assert recuperado.correo == "ana@empresa.com"
    assert recuperado.hash_contrasena == "$2b$12$hashalmacenado"
    assert recuperado.rol is RolUsuario.AUDITOR_SST
    assert recuperado.activo is True


async def test_should_buscar_por_correo_normalizado_a_minusculas(sesion: AsyncSession) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)
    await repositorio.guardar(construir_usuario())

    # La consulta normaliza a minúsculas aunque el llamador pase mayúsculas.
    encontrado = await repositorio.buscar_por_correo("ANA@EMPRESA.COM")

    assert encontrado is not None
    assert encontrado.correo == "ana@empresa.com"


async def test_should_devolver_none_when_usuario_no_existe(sesion: AsyncSession) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)

    assert await repositorio.buscar_por_correo("nadie@empresa.com") is None
    assert await repositorio.buscar_por_id(uuid4()) is None


async def test_should_reportar_existencia_por_correo(sesion: AsyncSession) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)
    await repositorio.guardar(construir_usuario())

    assert await repositorio.existe_por_correo("ana@empresa.com") is True
    assert await repositorio.existe_por_correo("nadie@empresa.com") is False


async def test_should_actualizar_usuario_existente_when_guardar_con_id(
    sesion: AsyncSession,
) -> None:
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)
    guardado = await repositorio.guardar(construir_usuario())
    guardado.activo = False

    actualizado = await repositorio.guardar(guardado)

    assert actualizado.id == guardado.id
    assert actualizado.activo is False
