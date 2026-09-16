"""Pruebas unitarias de `ServicioMatrizRiesgos` — repositorios mockeados."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.dto.matriz_riesgo import (
    SolicitudCrearProcesoActividad,
    SolicitudUpsertEvaluacion,
)
from src.application.services.servicio_matriz_riesgos import ServicioMatrizRiesgos
from src.domain.exceptions.autoevaluacion import EmpresaNoEncontradaError
from src.domain.exceptions.matriz_riesgo import (
    ControlNoEncontradoError,
    EvaluacionNoEncontradaError,
    PeligroNoEncontradoError,
    ProcesoNoEncontradoError,
)
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.gtc45 import ClasificacionPeligro
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad


@pytest.fixture
def repos() -> dict[str, AsyncMock]:
    return {
        "empresa": AsyncMock(),
        "proceso": AsyncMock(),
        "peligro": AsyncMock(),
        "evaluacion": AsyncMock(),
        "control": AsyncMock(),
    }


@pytest.fixture
def servicio(repos: dict[str, AsyncMock]) -> ServicioMatrizRiesgos:
    return ServicioMatrizRiesgos(
        repositorio_empresa=repos["empresa"],
        repositorio_proceso=repos["proceso"],
        repositorio_peligro=repos["peligro"],
        repositorio_evaluacion=repos["evaluacion"],
        repositorio_control=repos["control"],
    )


def _proceso(empresa_id: object | None = None) -> ProcesoActividad:
    proceso = ProcesoActividad.crear(
        empresa_id=empresa_id or uuid4(),
        nombre="Soldadura",
        es_rutinaria=True,
        zona_lugar="Taller",
    )
    proceso.id = uuid4()
    proceso.fecha_creacion = datetime.now(UTC)
    proceso.fecha_actualizacion = datetime.now(UTC)
    return proceso


def _peligro(proceso_id: object | None = None) -> Peligro:
    peligro = Peligro.crear(
        proceso_actividad_id=proceso_id or uuid4(),
        clasificacion=ClasificacionPeligro.FISICO,
        descripcion="Ruido",
        efectos_posibles=None,
    )
    peligro.id = uuid4()
    peligro.fecha_creacion = datetime.now(UTC)
    peligro.fecha_actualizacion = datetime.now(UTC)
    return peligro


async def test_should_lanzar_empresa_no_encontrada_when_crear_proceso(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    repos["empresa"].buscar_por_id.return_value = None

    with pytest.raises(EmpresaNoEncontradaError):
        await servicio.crear_proceso(
            uuid4(),
            SolicitudCrearProcesoActividad(nombre="X", es_rutinaria=True),
        )


async def test_should_lanzar_proceso_no_encontrado_when_obtener(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    repos["proceso"].buscar_por_id.return_value = None

    with pytest.raises(ProcesoNoEncontradoError):
        await servicio.obtener_proceso(uuid4())


async def test_should_lanzar_peligro_no_encontrado_when_obtener(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    repos["peligro"].buscar_por_id.return_value = None

    with pytest.raises(PeligroNoEncontradoError):
        await servicio.obtener_peligro(uuid4())


async def test_should_lanzar_evaluacion_no_encontrada_when_obtener(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    peligro = _peligro()
    repos["peligro"].buscar_por_id.return_value = peligro
    repos["evaluacion"].buscar_por_peligro.return_value = None

    with pytest.raises(EvaluacionNoEncontradaError):
        await servicio.obtener_evaluacion(peligro.id)  # type: ignore[arg-type]


async def test_should_lanzar_control_no_encontrado_when_eliminar(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    repos["control"].eliminar.return_value = False

    with pytest.raises(ControlNoEncontradoError):
        await servicio.eliminar_control(uuid4())


async def test_should_crear_evaluacion_when_upsert_sin_existente(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    peligro = _peligro()
    repos["peligro"].buscar_por_id.return_value = peligro
    repos["evaluacion"].buscar_por_peligro.return_value = None

    async def _guardar(evaluacion: EvaluacionRiesgo) -> EvaluacionRiesgo:
        evaluacion.id = uuid4()
        return evaluacion

    repos["evaluacion"].guardar.side_effect = _guardar

    respuesta, creado = await servicio.upsert_evaluacion(
        peligro.id,  # type: ignore[arg-type]
        SolicitudUpsertEvaluacion(
            nivel_deficiencia=2,
            nivel_exposicion=2,
            nivel_consecuencia=25,
        ),
    )

    assert creado is True
    assert respuesta.nivel_riesgo == 100
    assert respuesta.interpretacion_nr == "III"


async def test_should_actualizar_evaluacion_when_upsert_con_existente(
    servicio: ServicioMatrizRiesgos,
    repos: dict[str, AsyncMock],
) -> None:
    peligro = _peligro()
    existente = EvaluacionRiesgo.crear(
        peligro_id=peligro.id,  # type: ignore[arg-type]
        nivel_deficiencia=10,
        nivel_exposicion=4,
        nivel_consecuencia=100,
    )
    existente.id = uuid4()
    repos["peligro"].buscar_por_id.return_value = peligro
    repos["evaluacion"].buscar_por_peligro.return_value = existente
    repos["evaluacion"].guardar.side_effect = lambda e: e

    respuesta, creado = await servicio.upsert_evaluacion(
        peligro.id,  # type: ignore[arg-type]
        SolicitudUpsertEvaluacion(
            nivel_deficiencia=0,
            nivel_exposicion=4,
            nivel_consecuencia=100,
        ),
    )

    assert creado is False
    assert respuesta.nivel_riesgo == 0
    assert respuesta.interpretacion_nr == "IV"
