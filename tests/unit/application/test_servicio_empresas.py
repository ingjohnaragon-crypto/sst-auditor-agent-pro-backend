"""Pruebas unitarias de `ServicioEmpresas` — repositorio mockeado."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.dto.solicitud_crear_empresa import SolicitudCrearEmpresa
from src.application.services.servicio_empresas import ServicioEmpresas
from src.domain.exceptions.autoevaluacion import (
    EmpresaNoEncontradaError,
    NitDuplicadoError,
)
from src.domain.models.empresa import Empresa


def construir_empresa(*, nit: str = "900123456-1") -> Empresa:
    empresa = Empresa.crear(
        razon_social="Acme SST SAS",
        nit=nit,
        actividad_economica="Actividades de consultoría",
        nivel_riesgo_arl="III",
        numero_trabajadores=25,
    )
    empresa.id = uuid4()
    empresa.fecha_creacion = datetime.now(UTC)
    empresa.fecha_actualizacion = datetime.now(UTC)
    return empresa


def construir_dto() -> SolicitudCrearEmpresa:
    return SolicitudCrearEmpresa(
        razon_social="Acme SST SAS",
        nit="900123456-1",
        actividad_economica="Actividades de consultoría",
        nivel_riesgo_arl="III",
        numero_trabajadores=25,
    )


@pytest.fixture
def repositorio() -> AsyncMock:
    return AsyncMock()


async def test_should_crear_empresa_when_nit_disponible(repositorio: AsyncMock) -> None:
    repositorio.buscar_por_nit.return_value = None
    guardada = construir_empresa()
    repositorio.guardar.return_value = guardada
    servicio = ServicioEmpresas(repositorio)

    respuesta = await servicio.crear(construir_dto())

    assert respuesta.id == guardada.id
    assert respuesta.nit == guardada.nit
    repositorio.guardar.assert_awaited_once()


async def test_should_lanzar_nit_duplicado_when_nit_existe(repositorio: AsyncMock) -> None:
    repositorio.buscar_por_nit.return_value = construir_empresa()
    servicio = ServicioEmpresas(repositorio)

    with pytest.raises(NitDuplicadoError) as exc_info:
        await servicio.crear(construir_dto())

    assert exc_info.value.code == "NIT_DUPLICADO"
    repositorio.guardar.assert_not_awaited()


async def test_should_listar_empresas(repositorio: AsyncMock) -> None:
    empresas = [construir_empresa(nit="1"), construir_empresa(nit="2")]
    repositorio.listar.return_value = empresas
    servicio = ServicioEmpresas(repositorio)

    respuesta = await servicio.listar()

    assert len(respuesta) == 2
    assert {r.nit for r in respuesta} == {"1", "2"}


async def test_should_obtener_empresa_when_existe(repositorio: AsyncMock) -> None:
    empresa = construir_empresa()
    repositorio.buscar_por_id.return_value = empresa
    servicio = ServicioEmpresas(repositorio)

    respuesta = await servicio.obtener(empresa.id)  # type: ignore[arg-type]

    assert respuesta.id == empresa.id


async def test_should_lanzar_empresa_no_encontrada_when_id_inexistente(
    repositorio: AsyncMock,
) -> None:
    repositorio.buscar_por_id.return_value = None
    servicio = ServicioEmpresas(repositorio)

    with pytest.raises(EmpresaNoEncontradaError) as exc_info:
        await servicio.obtener(uuid4())

    assert exc_info.value.code == "EMPRESA_NO_ENCONTRADA"
