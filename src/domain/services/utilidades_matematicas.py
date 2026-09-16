"""Primitivas matemáticas compartidas para indicadores del SG-SST."""

from decimal import ROUND_HALF_UP, Decimal

from src.domain.exceptions.estadisticas_sst import ValorEstadisticoInvalidoError

PRECISION_DOS_DECIMALES = Decimal("0.01")


def redondear_dos_decimales(valor: Decimal) -> Decimal:
    """Redondea un valor finito a dos decimales con empate hacia arriba."""
    _validar_finito(valor, "valor")
    return valor.quantize(PRECISION_DOS_DECIMALES, rounding=ROUND_HALF_UP)


def validar_no_negativo(valor: Decimal | int, nombre_campo: str) -> None:
    """Valida que un número sea finito y mayor o igual a cero."""
    valor_decimal = _convertir_decimal(valor)
    _validar_finito(valor_decimal, nombre_campo)
    if valor_decimal < 0:
        raise ValorEstadisticoInvalidoError(
            f"El campo {nombre_campo} debe ser mayor o igual a cero"
        )


def validar_positivo(valor: Decimal | int, nombre_campo: str) -> None:
    """Valida que un número sea finito y estrictamente positivo."""
    valor_decimal = _convertir_decimal(valor)
    _validar_finito(valor_decimal, nombre_campo)
    if valor_decimal <= 0:
        raise ValorEstadisticoInvalidoError(f"El campo {nombre_campo} debe ser mayor que cero")


def dividir_seguro(
    numerador: Decimal,
    denominador: Decimal,
    nombre_denominador: str,
) -> Decimal:
    """Divide valores finitos y rechaza denominadores no positivos."""
    _validar_finito(numerador, "numerador")
    validar_positivo(denominador, nombre_denominador)
    return numerador / denominador


def _convertir_decimal(valor: Decimal | int) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(valor)


def _validar_finito(valor: Decimal, nombre_campo: str) -> None:
    if not valor.is_finite():
        raise ValorEstadisticoInvalidoError(f"El campo {nombre_campo} debe ser un número finito")
