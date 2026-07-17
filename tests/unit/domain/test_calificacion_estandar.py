"""Pruebas de la derivación de puntaje en `CalificacionEstandar`."""

from decimal import Decimal
from uuid import uuid4

from src.domain.models.autoevaluacion import CalificacionEstandar, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo


def _estandar(valor: str = "2.50") -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral="1.1.1",
        descripcion="Política",
        valor_porcentual=Decimal(valor),
    )


def test_should_asignar_valor_porcentual_when_resultado_cumple() -> None:
    estandar = _estandar("2.50")

    cal = CalificacionEstandar.calificar(estandar, ResultadoCalificacion.CUMPLE)

    assert cal.puntaje == Decimal("2.50")
    assert cal.estandar_id == estandar.id


def test_should_asignar_valor_porcentual_when_resultado_no_aplica() -> None:
    estandar = _estandar("1.00")

    cal = CalificacionEstandar.calificar(estandar, ResultadoCalificacion.NO_APLICA)

    assert cal.puntaje == Decimal("1.00")


def test_should_asignar_cero_when_resultado_no_cumple() -> None:
    estandar = _estandar("2.50")

    cal = CalificacionEstandar.calificar(estandar, ResultadoCalificacion.NO_CUMPLE)

    assert cal.puntaje == Decimal("0")
