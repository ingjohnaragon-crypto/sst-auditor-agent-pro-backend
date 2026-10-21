"""Pruebas del agregado `PlanMejora` y de las actividades del cronograma."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from src.domain.exceptions.plan_mejora import (
    ActividadCronogramaInvalidaError,
    AutoevaluacionEnBorradorError,
    AutoevaluacionSinPersistirError,
    PlanMejoraNoRequeridoError,
)
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.models.plan_mejora import PlanMejora


def _estandar(valor: str) -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral=str(uuid4())[:8],
        descripcion="Ítem",
        valor_porcentual=Decimal(valor),
    )


def _finalizada(valor: str, *, con_id: bool = True) -> Autoevaluacion:
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 3, 1))
    auto.calificar(_estandar(valor), ResultadoCalificacion.CUMPLE)
    auto.finalizar(total_requerido=1)
    if con_id:
        auto.id = uuid4()
    return auto


def test_should_copiar_vinculo_when_la_autoevaluacion_requiere_plan() -> None:
    auto = _finalizada("84.99")

    plan = PlanMejora.crear(auto)

    assert plan.id is None
    assert plan.empresa_id == auto.empresa_id
    assert plan.autoevaluacion_id == auto.id
    assert plan.actividades == []


def test_should_lanzar_borrador_when_no_esta_finalizada() -> None:
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 3, 1))
    auto.id = uuid4()

    with pytest.raises(AutoevaluacionEnBorradorError):
        PlanMejora.crear(auto)


def test_should_lanzar_no_requerido_when_puntaje_alcanza_el_umbral() -> None:
    auto = _finalizada("85.00")

    with pytest.raises(PlanMejoraNoRequeridoError):
        PlanMejora.crear(auto)


def test_should_lanzar_sin_persistir_when_id_es_null() -> None:
    auto = _finalizada("84.99", con_id=False)

    with pytest.raises(AutoevaluacionSinPersistirError):
        PlanMejora.crear(auto)


def test_should_ordenar_meses_when_agregar_actividad() -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    actividad = plan.agregar_actividad(
        "  Designar responsable  ",
        "  Coordinador SST  ",
        "  Acta de nombramiento  ",
        [12, 1],
    )

    assert actividad.id is None
    assert actividad.descripcion == "Designar responsable"
    assert actividad.responsable == "Coordinador SST"
    assert actividad.indicador == "Acta de nombramiento"
    assert actividad.meses == (1, 12)
    assert plan.actividades == [actividad]


@pytest.mark.parametrize("mes", [0, 13])
def test_should_lanzar_when_mes_fuera_de_rango(mes: int) -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad("Capacitar", "Jefe SST", "Listado", [mes])


def test_should_lanzar_when_no_hay_meses() -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad("Capacitar", "Jefe SST", "Listado", [])


def test_should_lanzar_when_mes_esta_repetido() -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad("Capacitar", "Jefe SST", "Listado", [3, 3])


@pytest.mark.parametrize(
    ("descripcion", "responsable", "indicador"),
    [
        ("", "Jefe SST", "Listado"),
        ("   ", "Jefe SST", "Listado"),
        ("Capacitar", "", "Listado"),
        ("Capacitar", "   ", "Listado"),
        ("Capacitar", "Jefe SST", ""),
        ("Capacitar", "Jefe SST", "   "),
    ],
)
def test_should_lanzar_when_texto_vacio(descripcion: str, responsable: str, indicador: str) -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad(descripcion, responsable, indicador, [1])


def test_should_lanzar_when_responsable_excede_largo() -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad("Capacitar", "a" * 151, "Listado", [1])


def test_should_lanzar_when_indicador_excede_largo() -> None:
    plan = PlanMejora.crear(_finalizada("84.99"))

    with pytest.raises(ActividadCronogramaInvalidaError):
        plan.agregar_actividad("Capacitar", "Jefe SST", "a" * 201, [1])
