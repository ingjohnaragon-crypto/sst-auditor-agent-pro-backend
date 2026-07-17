"""Pruebas unitarias de `ServicioAutoevaluaciones` — repositorios mockeados."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from src.application.dto.solicitud_calificar_estandar import SolicitudCalificarEstandar
from src.application.dto.solicitud_crear_autoevaluacion import (
    SolicitudCrearAutoevaluacion,
)
from src.application.services.servicio_autoevaluaciones import ServicioAutoevaluaciones
from src.domain.exceptions.autoevaluacion import (
    AutoevaluacionNoEncontradaError,
    EmpresaNoEncontradaError,
    EstandarNoEncontradoError,
)
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.empresa import Empresa
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo


def construir_empresa() -> Empresa:
    empresa = Empresa.crear(
        razon_social="Acme SST SAS",
        nit="900123456-1",
        actividad_economica="Consultoría",
        nivel_riesgo_arl="II",
        numero_trabajadores=10,
    )
    empresa.id = uuid4()
    return empresa


def construir_autoevaluacion(
    *, empresa_id: UUID | None = None, usuario_id: UUID | None = None
) -> Autoevaluacion:
    auto = Autoevaluacion.crear(
        empresa_id=empresa_id or uuid4(),
        usuario_id=usuario_id or uuid4(),
        fecha=date(2026, 7, 17),
    )
    auto.id = uuid4()
    auto.fecha_creacion = datetime.now(UTC)
    auto.fecha_actualizacion = datetime.now(UTC)
    return auto


def construir_estandar() -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral="1.1.1",
        descripcion="Recursos financieros",
        valor_porcentual=Decimal("0.50"),
    )


@pytest.fixture
def repo_autoevaluacion() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo_empresa() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo_estandar() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def servicio(
    repo_autoevaluacion: AsyncMock,
    repo_empresa: AsyncMock,
    repo_estandar: AsyncMock,
) -> ServicioAutoevaluaciones:
    return ServicioAutoevaluaciones(
        repositorio_autoevaluacion=repo_autoevaluacion,
        repositorio_empresa=repo_empresa,
        repositorio_estandar_minimo=repo_estandar,
    )


async def test_should_crear_autoevaluacion_when_empresa_existe(
    servicio: ServicioAutoevaluaciones,
    repo_empresa: AsyncMock,
    repo_autoevaluacion: AsyncMock,
) -> None:
    empresa = construir_empresa()
    repo_empresa.buscar_por_id.return_value = empresa
    guardada = construir_autoevaluacion(empresa_id=empresa.id)
    repo_autoevaluacion.guardar.return_value = guardada
    usuario_id = uuid4()
    dto = SolicitudCrearAutoevaluacion(empresa_id=empresa.id, fecha=date(2026, 7, 17))  # type: ignore[arg-type]

    respuesta = await servicio.crear(dto, usuario_id)

    assert respuesta.id == guardada.id
    assert respuesta.empresa_id == empresa.id
    repo_autoevaluacion.guardar.assert_awaited_once()


async def test_should_lanzar_empresa_no_encontrada_when_crear_con_empresa_inexistente(
    servicio: ServicioAutoevaluaciones,
    repo_empresa: AsyncMock,
    repo_autoevaluacion: AsyncMock,
) -> None:
    repo_empresa.buscar_por_id.return_value = None
    dto = SolicitudCrearAutoevaluacion(empresa_id=uuid4(), fecha=date(2026, 7, 17))

    with pytest.raises(EmpresaNoEncontradaError) as exc_info:
        await servicio.crear(dto, uuid4())

    assert exc_info.value.code == "EMPRESA_NO_ENCONTRADA"
    repo_autoevaluacion.guardar.assert_not_awaited()


async def test_should_lanzar_estandar_no_encontrado_when_calificar_estandar_inexistente(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
    repo_estandar: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    repo_autoevaluacion.buscar_por_id.return_value = auto
    repo_estandar.buscar_por_id.return_value = None
    dto = SolicitudCalificarEstandar(resultado="CUMPLE")

    with pytest.raises(EstandarNoEncontradoError) as exc_info:
        await servicio.calificar(auto.id, uuid4(), dto)  # type: ignore[arg-type]

    assert exc_info.value.code == "ESTANDAR_NO_ENCONTRADO"
    repo_autoevaluacion.guardar.assert_not_awaited()


async def test_should_calificar_y_persistir_when_datos_validos(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
    repo_estandar: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    estandar = construir_estandar()
    repo_autoevaluacion.buscar_por_id.return_value = auto
    repo_estandar.buscar_por_id.return_value = estandar
    repo_autoevaluacion.guardar.return_value = auto
    dto = SolicitudCalificarEstandar(resultado="CUMPLE", observaciones="OK")

    respuesta = await servicio.calificar(auto.id, estandar.id, dto)  # type: ignore[arg-type]

    assert respuesta.estandar_id == estandar.id
    assert respuesta.resultado == ResultadoCalificacion.CUMPLE.value
    assert respuesta.puntaje == estandar.valor_porcentual
    repo_autoevaluacion.guardar.assert_awaited_once()
    assert estandar.id in auto.calificaciones


async def test_should_reutilizar_calificacion_when_upsert(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
    repo_estandar: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    estandar = construir_estandar()
    primera = auto.calificar(estandar, ResultadoCalificacion.NO_CUMPLE)
    primera.id = uuid4()
    repo_autoevaluacion.buscar_por_id.return_value = auto
    repo_estandar.buscar_por_id.return_value = estandar
    repo_autoevaluacion.guardar.return_value = auto
    dto = SolicitudCalificarEstandar(resultado="CUMPLE")

    respuesta = await servicio.calificar(auto.id, estandar.id, dto)  # type: ignore[arg-type]

    assert respuesta.puntaje == estandar.valor_porcentual
    assert len(auto.calificaciones) == 1
    assert auto.calificaciones[estandar.id].id == primera.id


async def test_should_lanzar_autoevaluacion_no_encontrada_when_obtener_inexistente(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
) -> None:
    repo_autoevaluacion.buscar_por_id.return_value = None

    with pytest.raises(AutoevaluacionNoEncontradaError):
        await servicio.obtener(uuid4())


async def test_should_obtener_detalle_con_calificaciones(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    estandar = construir_estandar()
    auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    repo_autoevaluacion.buscar_por_id.return_value = auto

    assert auto.id is not None
    respuesta = await servicio.obtener(auto.id)

    assert len(respuesta.calificaciones) == 1
    assert respuesta.calificaciones[0].estandar_id == estandar.id


async def test_should_listar_por_empresa_sin_calificaciones_embebidas(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    estandar = construir_estandar()
    auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    repo_autoevaluacion.listar_por_empresa.return_value = [auto]

    respuesta = await servicio.listar_por_empresa(auto.empresa_id)

    assert len(respuesta) == 1
    assert respuesta[0].calificaciones == []


async def test_should_lanzar_autoevaluacion_no_encontrada_when_calificar_inexistente(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
) -> None:
    repo_autoevaluacion.buscar_por_id.return_value = None
    dto = SolicitudCalificarEstandar(resultado="CUMPLE")

    with pytest.raises(AutoevaluacionNoEncontradaError):
        await servicio.calificar(uuid4(), uuid4(), dto)


async def test_should_lanzar_autoevaluacion_no_encontrada_when_finalizar_inexistente(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
) -> None:
    repo_autoevaluacion.buscar_por_id.return_value = None

    with pytest.raises(AutoevaluacionNoEncontradaError):
        await servicio.finalizar(uuid4())


async def test_should_finalizar_usando_contar_como_total_requerido(
    servicio: ServicioAutoevaluaciones,
    repo_autoevaluacion: AsyncMock,
    repo_estandar: AsyncMock,
) -> None:
    auto = construir_autoevaluacion()
    estandar = construir_estandar()
    auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    repo_autoevaluacion.buscar_por_id.return_value = auto
    repo_estandar.contar.return_value = 1
    repo_autoevaluacion.guardar.return_value = auto

    respuesta = await servicio.finalizar(auto.id)  # type: ignore[arg-type]

    assert respuesta.puntaje_total == estandar.valor_porcentual
    assert respuesta.requiere_plan_mejora is True
    repo_estandar.contar.assert_awaited_once()


async def test_should_listar_estandares_filtrados_por_ciclo(
    servicio: ServicioAutoevaluaciones,
    repo_estandar: AsyncMock,
) -> None:
    estandar = construir_estandar()
    repo_estandar.listar.return_value = [estandar]

    respuesta = await servicio.listar_estandares(CicloPHVA.PLANEAR)

    assert len(respuesta) == 1
    assert respuesta[0].ciclo_phva == "PLANEAR"
    repo_estandar.listar.assert_awaited_once_with(CicloPHVA.PLANEAR)
