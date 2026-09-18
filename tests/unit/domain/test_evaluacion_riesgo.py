"""Pruebas del cálculo Anexo A / decisión D1 de `EvaluacionRiesgo`."""

from uuid import uuid4

import pytest
from src.domain.exceptions.matriz_riesgo import ValorGtcInvalidoError
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo, interpretar_nr
from src.domain.models.gtc45 import (
    ACEPTABILIDAD_POR_INTERPRETACION,
    ND_VALIDOS,
    NE_VALIDOS,
    AceptabilidadRiesgo,
    InterpretacionNR,
)


def test_should_calcular_nr_muy_alto_when_nd10_ne4_nc100() -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), 10, 4, 100)
    assert ev.nivel_probabilidad == 40
    assert ev.nivel_riesgo == 4000
    assert ev.interpretacion_nr == InterpretacionNR.I
    assert ev.aceptabilidad == AceptabilidadRiesgo.NO_ACEPTABLE


def test_should_interpretar_iv_when_nd_cero_decision_d1() -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), 0, 4, 100)
    assert ev.nivel_probabilidad == 0
    assert ev.nivel_riesgo == 0
    assert ev.interpretacion_nr == InterpretacionNR.IV
    assert ev.aceptabilidad == AceptabilidadRiesgo.ACEPTABLE


@pytest.mark.parametrize(
    ("nd", "ne", "nc", "nr", "interpretacion", "aceptabilidad"),
    [
        (6, 4, 25, 600, InterpretacionNR.I, AceptabilidadRiesgo.NO_ACEPTABLE),
        (10, 2, 25, 500, InterpretacionNR.II, AceptabilidadRiesgo.ACEPTABLE_CON_CONTROL),
        (6, 2, 10, 120, InterpretacionNR.III, AceptabilidadRiesgo.MEJORABLE),
        (2, 1, 10, 20, InterpretacionNR.IV, AceptabilidadRiesgo.ACEPTABLE),
    ],
)
def test_should_mapear_bordes_a3(
    nd: int,
    ne: int,
    nc: int,
    nr: int,
    interpretacion: InterpretacionNR,
    aceptabilidad: AceptabilidadRiesgo,
) -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), nd, ne, nc)
    assert ev.nivel_probabilidad == nd * ne
    assert ev.nivel_riesgo == nr
    assert ev.interpretacion_nr == interpretacion
    assert ev.aceptabilidad == aceptabilidad


@pytest.mark.parametrize("nd", sorted(ND_VALIDOS))
@pytest.mark.parametrize("ne", sorted(NE_VALIDOS))
def test_should_calcular_np_como_producto_when_nd_y_ne_validos(nd: int, ne: int) -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), nd, ne, 10)
    assert ev.nivel_probabilidad == nd * ne


def test_should_lanzar_when_nd_invalido() -> None:
    with pytest.raises(ValorGtcInvalidoError, match="deficiencia"):
        EvaluacionRiesgo.crear(uuid4(), 5, 2, 10)


def test_should_lanzar_when_ne_invalido() -> None:
    with pytest.raises(ValorGtcInvalidoError, match="exposición"):
        EvaluacionRiesgo.crear(uuid4(), 2, 5, 10)


def test_should_lanzar_when_nc_invalido() -> None:
    with pytest.raises(ValorGtcInvalidoError, match="consecuencia"):
        EvaluacionRiesgo.crear(uuid4(), 2, 2, 50)


def test_should_recalcular_derivados_when_put() -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), 10, 4, 100)
    ev.id = uuid4()
    ev.recalcular(0, 1, 10)
    assert ev.nivel_probabilidad == 0
    assert ev.nivel_riesgo == 0
    assert ev.interpretacion_nr == InterpretacionNR.IV
    assert ev.aceptabilidad == AceptabilidadRiesgo.ACEPTABLE


def test_should_actualizar_np_when_recalcular_nd_ne() -> None:
    ev = EvaluacionRiesgo.crear(uuid4(), 10, 4, 100)
    ev.id = uuid4()
    ev.recalcular(6, 3, 25)
    assert ev.nivel_probabilidad == 18
    assert ev.nivel_riesgo == 450
    assert ev.interpretacion_nr == InterpretacionNR.II
    assert ev.aceptabilidad == AceptabilidadRiesgo.ACEPTABLE_CON_CONTROL


@pytest.mark.parametrize(
    ("nr", "interpretacion"),
    [
        (0, InterpretacionNR.IV),
        (20, InterpretacionNR.IV),
        (40, InterpretacionNR.III),
        (120, InterpretacionNR.III),
        (150, InterpretacionNR.II),
        (500, InterpretacionNR.II),
        (600, InterpretacionNR.I),
        (4000, InterpretacionNR.I),
    ],
)
def test_should_interpretar_bordes_a3_when_nr_en_rango(
    nr: int, interpretacion: InterpretacionNR
) -> None:
    assert interpretar_nr(nr) == interpretacion


def test_should_mapear_aceptabilidad_when_interpretacion_a3() -> None:
    assert ACEPTABILIDAD_POR_INTERPRETACION[InterpretacionNR.I] == AceptabilidadRiesgo.NO_ACEPTABLE
    assert (
        ACEPTABILIDAD_POR_INTERPRETACION[InterpretacionNR.II]
        == AceptabilidadRiesgo.ACEPTABLE_CON_CONTROL
    )
    assert ACEPTABILIDAD_POR_INTERPRETACION[InterpretacionNR.III] == AceptabilidadRiesgo.MEJORABLE
    assert ACEPTABILIDAD_POR_INTERPRETACION[InterpretacionNR.IV] == AceptabilidadRiesgo.ACEPTABLE


def test_should_lanzar_when_nr_fuera_de_tabla_a3() -> None:
    with pytest.raises(ValorGtcInvalidoError, match="tabla A.3"):
        interpretar_nr(21)
