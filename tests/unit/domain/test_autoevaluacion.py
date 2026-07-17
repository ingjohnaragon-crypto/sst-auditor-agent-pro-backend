"""Pruebas del agregado `Autoevaluacion` (finalizar, umbral, inmutabilidad)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from src.domain.exceptions.autoevaluacion import (
    AutoevaluacionFinalizadaError,
    AutoevaluacionIncompletaError,
)
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo


def _estandar(valor: str) -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral=str(uuid4())[:8],
        descripcion="Ítem",
        valor_porcentual=Decimal(valor),
    )


def _autoevaluacion() -> Autoevaluacion:
    return Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 1, 15))


def test_should_sumar_puntaje_total_when_finalizar() -> None:
    auto = _autoevaluacion()
    e1, e2 = _estandar("50.00"), _estandar("35.00")
    auto.calificar(e1, ResultadoCalificacion.CUMPLE)
    auto.calificar(e2, ResultadoCalificacion.CUMPLE)

    auto.finalizar(total_requerido=2)

    assert auto.puntaje_total == Decimal("85.00")
    assert auto.requiere_plan_mejora is False


def test_should_requerir_plan_when_puntaje_bajo_umbral() -> None:
    auto = _autoevaluacion()
    e1, e2 = _estandar("50.00"), _estandar("34.99")
    auto.calificar(e1, ResultadoCalificacion.CUMPLE)
    auto.calificar(e2, ResultadoCalificacion.CUMPLE)

    auto.finalizar(total_requerido=2)

    assert auto.puntaje_total == Decimal("84.99")
    assert auto.requiere_plan_mejora is True


def test_should_no_requerir_plan_when_puntaje_exacto_85() -> None:
    auto = _autoevaluacion()
    e1 = _estandar("85.00")
    auto.calificar(e1, ResultadoCalificacion.CUMPLE)

    auto.finalizar(total_requerido=1)

    assert auto.puntaje_total == Decimal("85.00")
    assert auto.requiere_plan_mejora is False


def test_should_lanzar_incompleta_when_faltan_estandares() -> None:
    auto = _autoevaluacion()
    auto.calificar(_estandar("1.00"), ResultadoCalificacion.CUMPLE)

    with pytest.raises(AutoevaluacionIncompletaError) as exc:
        auto.finalizar(total_requerido=60)

    assert exc.value.faltantes == 59


def test_should_lanzar_finalizada_when_recalificar_tras_finalizar() -> None:
    auto = _autoevaluacion()
    estandar = _estandar("10.00")
    auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    auto.finalizar(total_requerido=1)

    with pytest.raises(AutoevaluacionFinalizadaError):
        auto.calificar(estandar, ResultadoCalificacion.NO_CUMPLE)


def test_should_reemplazar_calificacion_when_recalificar_antes_de_finalizar() -> None:
    auto = _autoevaluacion()
    estandar = _estandar("10.00")
    auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    auto.calificar(estandar, ResultadoCalificacion.NO_CUMPLE)

    assert len(auto.calificaciones) == 1
    assert auto.calificaciones[estandar.id].puntaje == Decimal("0")


def test_should_lanzar_finalizada_when_refinalizar() -> None:
    auto = _autoevaluacion()
    auto.calificar(_estandar("10.00"), ResultadoCalificacion.CUMPLE)
    auto.finalizar(total_requerido=1)

    with pytest.raises(AutoevaluacionFinalizadaError):
        auto.finalizar(total_requerido=1)
