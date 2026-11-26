"""Pruebas del repositorio SQLAlchemy de archivos documentales."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import src.infrastructure.database.modelos  # noqa: F401 — registra las tablas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.models.archivo_documental import ArchivoDocumental, construir_clave_objeto
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.archivo_documental_orm import ArchivoDocumentalORM
from src.infrastructure.database.modelos.empresa_orm import EmpresaORM
from src.infrastructure.repositories.repositorio_archivo_documental_sqlalchemy import (
    RepositorioArchivoDocumentalSQLAlchemy,
)

HASH_VALIDO = "b" * 64


@pytest.fixture
async def sesion() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion_activa:
        yield sesion_activa
    await motor.dispose()


def test_should_declarar_clave_unica_e_indice_empresa() -> None:
    columnas_indice = [
        list(indice.columns.keys()) for indice in ArchivoDocumentalORM.__table__.indexes
    ]
    uniques = {restriccion.name for restriccion in ArchivoDocumentalORM.__table__.constraints}
    assert ["empresa_id"] in columnas_indice
    assert "uq_archivos_documentales_clave_objeto" in uniques


async def test_should_guardar_listar_buscar_y_eliminar(
    sesion: AsyncSession,
) -> None:
    empresa_id = uuid4()
    usuario_id = uuid4()
    sesion.add(
        EmpresaORM(
            id=empresa_id,
            razon_social="Acme",
            nit="900111222",
            actividad_economica="Consultoría",
            nivel_riesgo_arl="I",
            numero_trabajadores=10,
        )
    )
    await sesion.flush()

    repo = RepositorioArchivoDocumentalSQLAlchemy(sesion)
    assert await repo.existe_empresa(empresa_id) is True
    assert await repo.existe_empresa(uuid4()) is False

    primero = ArchivoDocumental.crear(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        nombre_original="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=100,
        hash_contenido=HASH_VALIDO,
        clave_objeto=construir_clave_objeto(empresa_id, ".pdf"),
    )
    segundo = ArchivoDocumental.crear(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        nombre_original="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=200,
        hash_contenido="c" * 64,
        clave_objeto=construir_clave_objeto(empresa_id, ".pdf"),
    )
    assert primero.clave_objeto != segundo.clave_objeto

    guardado = await repo.guardar(primero)
    await repo.guardar(segundo)
    assert guardado.id is not None

    listado = await repo.listar_por_empresa(empresa_id)
    assert len(listado) == 2
    assert {item.nombre_original for item in listado} == {"acta.pdf"}

    encontrado = await repo.buscar_por_id(guardado.id)
    assert encontrado is not None
    assert encontrado.clave_objeto == primero.clave_objeto
    assert encontrado.hash == HASH_VALIDO

    await repo.eliminar(guardado.id)
    assert await repo.buscar_por_id(guardado.id) is None
    assert len(await repo.listar_por_empresa(empresa_id)) == 1

    await repo.eliminar(guardado.id)  # idempotente
