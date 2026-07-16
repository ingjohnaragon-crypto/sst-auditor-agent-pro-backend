"""Fixtures de integración: app FastAPI + SQLite async en memoria + usuarios semilla."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.usuario_orm import UsuarioORM  # noqa: F401
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_usuario_sqlalchemy import (
    RepositorioUsuarioSQLAlchemy,
)
from src.infrastructure.security.hash_bcrypt import HashBcrypt
from src.main import app

CONTRASENA_VALIDA = "Password1!"
CORREO_ADMIN = "admin@empresa.com"
CORREO_CONSULTA = "consulta@empresa.com"
CORREO_INACTIVO = "inactivo@empresa.com"


@dataclass(frozen=True)
class UsuariosSemilla:
    """Identificadores de los usuarios creados en la BD de prueba."""

    correo_admin: str = CORREO_ADMIN
    correo_consulta: str = CORREO_CONSULTA
    correo_inactivo: str = CORREO_INACTIVO
    contrasena: str = CONTRASENA_VALIDA


@pytest.fixture
async def cliente_async() -> AsyncIterator[AsyncClient]:
    """Cliente HTTP async contra la app real con BD aiosqlite compartida (StaticPool)."""
    motor = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)

    async def override_obtener_sesion() -> AsyncIterator[AsyncSession]:
        async with fabrica() as sesion:
            try:
                yield sesion
                await sesion.commit()
            except Exception:
                await sesion.rollback()
                raise

    app.dependency_overrides[obtener_sesion] = override_obtener_sesion

    hash_servicio = HashBcrypt()
    hash_contrasena = await hash_servicio.generar_hash(CONTRASENA_VALIDA)
    async with fabrica() as sesion:
        repo = RepositorioUsuarioSQLAlchemy(sesion)
        await repo.guardar(
            Usuario.crear(
                nombre_completo="Admin Prueba",
                correo=CORREO_ADMIN,
                hash_contrasena=hash_contrasena,
                rol=RolUsuario.ADMINISTRADOR,
            )
        )
        await repo.guardar(
            Usuario.crear(
                nombre_completo="Consulta Prueba",
                correo=CORREO_CONSULTA,
                hash_contrasena=hash_contrasena,
                rol=RolUsuario.CONSULTA,
            )
        )
        inactivo = Usuario.crear(
            nombre_completo="Inactivo Prueba",
            correo=CORREO_INACTIVO,
            hash_contrasena=hash_contrasena,
            rol=RolUsuario.AUDITOR_SST,
        )
        inactivo.activo = False
        await repo.guardar(inactivo)
        await sesion.commit()

    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente

    app.dependency_overrides.clear()
    await motor.dispose()


@pytest.fixture
def usuarios_semilla() -> UsuariosSemilla:
    return UsuariosSemilla()
