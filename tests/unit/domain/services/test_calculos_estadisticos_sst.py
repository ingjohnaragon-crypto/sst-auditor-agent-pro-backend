"""Pruebas de indicadores de accidentalidad y metas anuales SST."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from src.domain.exceptions.estadisticas_sst import ValorEstadisticoInvalidoError
from src.domain.services.calculos_estadisticos_sst import (
    ResultadoMetaAnual,
    SentidoMeta,
    calcular_tasa_frecuencia,
    calcular_tasa_severidad,
    comparar_meta_anual,
    proyectar_valor_anual,
)


@pytest.mark.parametrize(
    ("accidentes", "horas", "factor", "esperado"),
    [
        (0, Decimal("480000"), Decimal("240000"), Decimal("0.00")),
        (2, Decimal("480000"), Decimal("240000"), Decimal("1.00")),
        (2, Decimal("100"), Decimal("1000"), Decimal("20.00")),
        (1, Decimal("700000"), Decimal("240000"), Decimal("0.34")),
    ],
)
def test_should_calcular_frecuencia_when_datos_validos(
    accidentes: int,
    horas: Decimal,
    factor: Decimal,
    esperado: Decimal,
) -> None:
    resultado = calcular_tasa_frecuencia(accidentes, horas, factor)

    assert resultado == esperado


@pytest.mark.parametrize(
    ("accidentes", "horas", "factor", "campo"),
    [
        (-1, Decimal("10"), Decimal("240000"), "numero_accidentes"),
        (1, Decimal("0"), Decimal("240000"), "horas_trabajadas"),
        (1, Decimal("-1"), Decimal("240000"), "horas_trabajadas"),
        (1, Decimal("10"), Decimal("0"), "factor"),
        (1, Decimal("10"), Decimal("-1"), "factor"),
    ],
)
def test_should_rechazar_frecuencia_when_dato_invalido(
    accidentes: int,
    horas: Decimal,
    factor: Decimal,
    campo: str,
) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match=campo):
        calcular_tasa_frecuencia(accidentes, horas, factor)


@pytest.mark.parametrize(
    ("incapacidad", "cargados", "esperado"),
    [
        (0, 0, Decimal("0.00")),
        (3, 0, Decimal("1.50")),
        (0, 2, Decimal("1.00")),
        (3, 2, Decimal("2.50")),
    ],
)
def test_should_calcular_severidad_when_datos_validos(
    incapacidad: int,
    cargados: int,
    esperado: Decimal,
) -> None:
    resultado = calcular_tasa_severidad(
        incapacidad,
        cargados,
        Decimal("480000"),
    )

    assert resultado == esperado


@pytest.mark.parametrize(
    ("incapacidad", "cargados", "horas", "factor", "campo"),
    [
        (-1, 0, Decimal("10"), Decimal("240000"), "dias_incapacidad"),
        (0, -1, Decimal("10"), Decimal("240000"), "dias_cargados"),
        (0, 0, Decimal("0"), Decimal("240000"), "horas_trabajadas"),
        (0, 0, Decimal("10"), Decimal("0"), "factor"),
    ],
)
def test_should_rechazar_severidad_when_dato_invalido(
    incapacidad: int,
    cargados: int,
    horas: Decimal,
    factor: Decimal,
    campo: str,
) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match=campo):
        calcular_tasa_severidad(incapacidad, cargados, horas, factor)


@pytest.mark.parametrize(
    ("acumulado", "transcurridos", "totales", "esperado"),
    [
        (Decimal("10"), 1, 12, Decimal("120.00")),
        (Decimal("30"), 3, 12, Decimal("120.00")),
        (Decimal("120"), 12, 12, Decimal("120.00")),
        (Decimal("0"), 6, 12, Decimal("0.00")),
        (Decimal("10"), 2, 4, Decimal("20.00")),
    ],
)
def test_should_proyectar_when_periodos_validos(
    acumulado: Decimal,
    transcurridos: int,
    totales: int,
    esperado: Decimal,
) -> None:
    assert proyectar_valor_anual(acumulado, transcurridos, totales) == esperado


@pytest.mark.parametrize(
    ("acumulado", "transcurridos", "totales", "campo"),
    [
        (Decimal("-1"), 1, 12, "valor_acumulado"),
        (Decimal("1"), 0, 12, "periodos_transcurridos"),
        (Decimal("1"), -1, 12, "periodos_transcurridos"),
        (Decimal("1"), 1, 0, "periodos_totales"),
        (Decimal("1"), 1, -1, "periodos_totales"),
        (Decimal("1"), 13, 12, "periodos_transcurridos"),
    ],
)
def test_should_rechazar_proyeccion_when_dato_invalido(
    acumulado: Decimal,
    transcurridos: int,
    totales: int,
    campo: str,
) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match=campo):
        proyectar_valor_anual(acumulado, transcurridos, totales)


@pytest.mark.parametrize(
    ("valor", "sentido", "cumplida"),
    [
        (Decimal("8"), SentidoMeta.MINIMIZAR, True),
        (Decimal("10"), SentidoMeta.MINIMIZAR, True),
        (Decimal("12"), SentidoMeta.MINIMIZAR, False),
        (Decimal("8"), SentidoMeta.MAXIMIZAR, False),
        (Decimal("10"), SentidoMeta.MAXIMIZAR, True),
        (Decimal("12"), SentidoMeta.MAXIMIZAR, True),
    ],
)
def test_should_evaluar_cumplimiento_when_sentido_valido(
    valor: Decimal,
    sentido: SentidoMeta,
    cumplida: bool,
) -> None:
    resultado = comparar_meta_anual(valor, Decimal("10"), sentido)

    assert resultado.cumplida is cumplida


def test_should_calcular_desviaciones_when_meta_positiva() -> None:
    resultado = comparar_meta_anual(
        Decimal("12.345"),
        Decimal("10"),
        SentidoMeta.MINIMIZAR,
    )

    assert resultado == ResultadoMetaAnual(
        valor_proyectado=Decimal("12.35"),
        meta=Decimal("10.00"),
        sentido=SentidoMeta.MINIMIZAR,
        cumplida=False,
        desviacion_absoluta=Decimal("2.35"),
        desviacion_porcentual=Decimal("23.50"),
    )


def test_should_conservar_desviacion_negativa_when_valor_inferior() -> None:
    resultado = comparar_meta_anual(
        Decimal("8"),
        Decimal("10"),
        SentidoMeta.MINIMIZAR,
    )

    assert resultado.desviacion_absoluta == Decimal("-2.00")
    assert resultado.desviacion_porcentual == Decimal("-20.00")


def test_should_omitir_porcentaje_when_meta_cero() -> None:
    resultado = comparar_meta_anual(
        Decimal("0"),
        Decimal("0"),
        SentidoMeta.MINIMIZAR,
    )

    assert resultado.cumplida is True
    assert resultado.desviacion_porcentual is None


@pytest.mark.parametrize(
    ("valor", "meta", "campo"),
    [
        (Decimal("-1"), Decimal("1"), "valor_proyectado"),
        (Decimal("1"), Decimal("-1"), "meta"),
    ],
)
def test_should_rechazar_meta_when_valor_negativo(
    valor: Decimal,
    meta: Decimal,
    campo: str,
) -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match=campo):
        comparar_meta_anual(valor, meta, SentidoMeta.MINIMIZAR)


def test_should_rechazar_meta_when_sentido_invalido() -> None:
    with pytest.raises(ValorEstadisticoInvalidoError, match="sentido"):
        comparar_meta_anual(
            Decimal("1"),
            Decimal("1"),
            "OTRO",  # type: ignore[arg-type]
        )


def test_should_ser_inmutable_when_resultado_creado() -> None:
    resultado = comparar_meta_anual(
        Decimal("1"),
        Decimal("2"),
        SentidoMeta.MAXIMIZAR,
    )

    with pytest.raises(FrozenInstanceError):
        resultado.cumplida = True  # type: ignore[misc]
