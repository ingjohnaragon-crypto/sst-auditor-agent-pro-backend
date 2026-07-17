"""Fixtures de integración: app FastAPI + SQLite async + usuarios y catálogo semilla."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos import (  # noqa: F401 — registra tablas
    AutoevaluacionORM,
    CalificacionEstandarORM,
    CatalogoReferenciaORM,
    EmpresaORM,
    EstandarMinimoORM,
    UsuarioORM,
)
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
    correo_admin: str = CORREO_ADMIN
    correo_consulta: str = CORREO_CONSULTA
    correo_inactivo: str = CORREO_INACTIVO
    contrasena: str = CONTRASENA_VALIDA


@dataclass(frozen=True)
class CatalogoSemilla:
    """IDs del catálogo reducido sembrado para integración (suma 85.00)."""

    estandar_ids: tuple[UUID, ...] = field(default_factory=tuple)


@pytest.fixture
async def cliente_async() -> AsyncIterator[AsyncClient]:
    """Cliente HTTP async con BD aiosqlite, usuarios y 3 estándares semilla."""
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
    ids_estandares: list[UUID] = []
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

        valores = (Decimal("10.00"), Decimal("10.00"), Decimal("65.00"))
        ciclos = ("PLANEAR", "HACER", "PLANEAR")
        for i, (valor, ciclo) in enumerate(zip(valores, ciclos, strict=True)):
            fila = EstandarMinimoORM(
                ciclo_phva=ciclo,
                numeral=f"INT-{i + 1}",
                descripcion=f"Ítem integración {i + 1}",
                valor_porcentual=valor,
            )
            sesion.add(fila)
            await sesion.flush()
            ids_estandares.append(fila.id)
        await sesion.commit()

    # Expone IDs en el cliente para tests (atributo auxiliar).
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        cliente.estandar_ids = tuple(ids_estandares)  # type: ignore[attr-defined]
        yield cliente

    app.dependency_overrides.clear()
    await motor.dispose()


@pytest.fixture
def usuarios_semilla() -> UsuariosSemilla:
    return UsuariosSemilla()


@pytest.fixture
def catalogo_semilla(cliente_async: AsyncClient) -> CatalogoSemilla:
    return CatalogoSemilla(estandar_ids=cliente_async.estandar_ids)  # type: ignore[attr-defined]
