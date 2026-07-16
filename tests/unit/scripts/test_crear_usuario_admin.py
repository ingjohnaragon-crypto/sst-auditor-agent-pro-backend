"""Pruebas del seed idempotente del administrador inicial."""

from collections.abc import AsyncIterator

import pytest
from scripts.crear_usuario_admin import crear_usuario_admin, leer_credenciales_del_entorno
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.usuario import RolUsuario
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.usuario_orm import UsuarioORM
from src.infrastructure.repositories.repositorio_usuario_sqlalchemy import (
    RepositorioUsuarioSQLAlchemy,
)

CORREO_ADMIN = "Admin@Empresa.com"
CONTRASENA_ADMIN = "ContrasenaAdmin123"


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


@pytest.fixture
def entorno_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_INICIAL_CORREO", CORREO_ADMIN)
    monkeypatch.setenv("ADMIN_INICIAL_CONTRASENA", CONTRASENA_ADMIN)
    monkeypatch.setenv("ADMIN_INICIAL_NOMBRE", "Administrador Inicial")


async def test_should_crear_administrador_when_no_existe(
    sesion: AsyncSession, entorno_admin: None
) -> None:
    creado = await crear_usuario_admin(sesion)

    assert creado is True
    usuario = await RepositorioUsuarioSQLAlchemy(sesion).buscar_por_correo(CORREO_ADMIN.lower())
    assert usuario is not None
    assert usuario.rol is RolUsuario.ADMINISTRADOR
    assert usuario.activo is True
    # La contraseña jamás se persiste en claro.
    assert usuario.hash_contrasena != CONTRASENA_ADMIN


async def test_should_ser_idempotente_when_el_correo_ya_existe(
    sesion: AsyncSession, entorno_admin: None
) -> None:
    primera_ejecucion = await crear_usuario_admin(sesion)
    segunda_ejecucion = await crear_usuario_admin(sesion)

    assert primera_ejecucion is True
    assert segunda_ejecucion is False
    total = (await sesion.execute(select(func.count()).select_from(UsuarioORM))).scalar_one()
    assert total == 1


def test_should_fallar_con_mensaje_claro_when_faltan_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_INICIAL_CORREO", raising=False)
    monkeypatch.delenv("ADMIN_INICIAL_CONTRASENA", raising=False)
    monkeypatch.delenv("ADMIN_INICIAL_NOMBRE", raising=False)

    with pytest.raises(RuntimeError, match="ADMIN_INICIAL_CORREO"):
        leer_credenciales_del_entorno()
