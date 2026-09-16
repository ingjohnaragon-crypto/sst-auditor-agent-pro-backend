"""Pruebas de las primitivas matemáticas compartidas."""

from decimal import Decimal

import pytest
from src.domain.exceptions.estadisticas_sst import ValorEstadisticoInvalidoError
from src.domain.services.utilidades_matematicas import (
    dividir_seguro,
    redondear_dos_decimales,
    validar_no_negativo,
    validar_positivo,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("1.234"), Decimal("1.23")),
        (Decimal("1.235"), Decimal("1.24")),
        (Decimal("-1.235"), Decimal("-1.24")),
        (Decimal("0"), Decimal("0.00")),
    ],
)
def test_should_redondear_half_up_when_valor_finito(
    valor: Decimal,
    esperado: Decimal,
) -> None:
    assert redondear_dos_decimales(valor) == esperado


@pytest.mark.parametrize("valor", [0, 1, Decimal("0"), Decimal("2.5")])
def test_should_aceptar_when_valor_no_negativo(valor: Decimal | int) -> None:
    validar_no_negativo(valor, "indicador")


@pytest.mark.parametrize("valor", [-1, Decimal("-0.01")])
def test_should_rechazar_when_valor_negativo(valor: Decimal | int) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="indicador"):
        validar_no_negativo(valor, "indicador")


@pytest.mark.parametrize("valor", [1, Decimal("0.01")])
def test_should_aceptar_when_valor_positivo(valor: Decimal | int) -> None:
    validar_positivo(valor, "denominador")


@pytest.mark.parametrize("valor", [0, -1, Decimal("-0.01")])
def test_should_rechazar_when_valor_no_positivo(valor: Decimal | int) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="denominador"):
        validar_positivo(valor, "denominador")


@pytest.mark.parametrize("valor", [Decimal("NaN"), Decimal("Infinity")])
def test_should_rechazar_when_valor_no_finito(valor: Decimal) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="finito"):
        validar_no_negativo(valor, "indicador")


def test_should_dividir_when_denominador_positivo() -> None:
    assert dividir_seguro(Decimal("10"), Decimal("4"), "horas") == Decimal("2.5")


@pytest.mark.parametrize("denominador", [Decimal("0"), Decimal("-1")])
def test_should_rechazar_division_when_denominador_no_positivo(
    denominador: Decimal,
) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="horas"):
        dividir_seguro(Decimal("10"), denominador, "horas")


def test_should_rechazar_division_when_numerador_no_finito() -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="numerador"):
        dividir_seguro(Decimal("NaN"), Decimal("1"), "horas")
