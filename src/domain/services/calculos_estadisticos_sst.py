"""Cálculos de accidentalidad, proyecciones y metas anuales del SG-SST."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.domain.exceptions.estadisticas_sst import ValorEstadisticoInvalidoError
from src.domain.services.utilidades_matematicas import (
    dividir_seguro,
    redondear_dos_decimales,
    validar_no_negativo,
    validar_positivo,
)

FACTOR_NORMALIZACION_SST = Decimal("240000")
PORCENTAJE = Decimal("100")


class SentidoMeta(StrEnum):
    """Indica si cumplir una meta exige disminuir o aumentar su indicador."""

    MINIMIZAR = "MINIMIZAR"
    MAXIMIZAR = "MAXIMIZAR"


@dataclass(frozen=True, slots=True)
class ResultadoMetaAnual:
    """Resultado inmutable de comparar un indicador proyectado con su meta."""

    valor_proyectado: Decimal
    meta: Decimal
    sentido: SentidoMeta
    cumplida: bool
    desviacion_absoluta: Decimal
    desviacion_porcentual: Decimal | None


def calcular_tasa_frecuencia(
    numero_accidentes: int,
    horas_trabajadas: Decimal,
    factor: Decimal = FACTOR_NORMALIZACION_SST,
) -> Decimal:
    """Calcula accidentes × factor / horas trabajadas, con dos decimales."""
    validar_no_negativo(numero_accidentes, "numero_accidentes")
    validar_positivo(horas_trabajadas, "horas_trabajadas")
    validar_positivo(factor, "factor")

    numerador = Decimal(numero_accidentes) * factor
    resultado = dividir_seguro(numerador, horas_trabajadas, "horas_trabajadas")
    return redondear_dos_decimales(resultado)


def calcular_tasa_severidad(
    dias_incapacidad: int,
    dias_cargados: int,
    horas_trabajadas: Decimal,
    factor: Decimal = FACTOR_NORMALIZACION_SST,
) -> Decimal:
    """Calcula (días de incapacidad + cargados) × factor / horas trabajadas."""
    validar_no_negativo(dias_incapacidad, "dias_incapacidad")
    validar_no_negativo(dias_cargados, "dias_cargados")
    validar_positivo(horas_trabajadas, "horas_trabajadas")
    validar_positivo(factor, "factor")

    total_dias = Decimal(dias_incapacidad + dias_cargados)
    resultado = dividir_seguro(
        total_dias * factor,
        horas_trabajadas,
        "horas_trabajadas",
    )
    return redondear_dos_decimales(resultado)


def proyectar_valor_anual(
    valor_acumulado: Decimal,
    periodos_transcurridos: int,
    periodos_totales: int = 12,
) -> Decimal:
    """Proyecta linealmente un acumulado al total de períodos indicado."""
    validar_no_negativo(valor_acumulado, "valor_acumulado")
    validar_positivo(periodos_transcurridos, "periodos_transcurridos")
    validar_positivo(periodos_totales, "periodos_totales")
    if periodos_transcurridos > periodos_totales:
        raise ValorEstadisticoInvalidoError(
            "El campo periodos_transcurridos no puede superar periodos_totales"
        )

    promedio = dividir_seguro(
        valor_acumulado,
        Decimal(periodos_transcurridos),
        "periodos_transcurridos",
    )
    return redondear_dos_decimales(promedio * Decimal(periodos_totales))


def comparar_meta_anual(
    valor_proyectado: Decimal,
    meta: Decimal,
    sentido: SentidoMeta,
) -> ResultadoMetaAnual:
    """Compara un valor con una meta y calcula sus desviaciones."""
    validar_no_negativo(valor_proyectado, "valor_proyectado")
    validar_no_negativo(meta, "meta")
    if not isinstance(sentido, SentidoMeta):
        raise ValorEstadisticoInvalidoError("El campo sentido debe ser MINIMIZAR o MAXIMIZAR")

    valor_normalizado = redondear_dos_decimales(valor_proyectado)
    meta_normalizada = redondear_dos_decimales(meta)
    desviacion_absoluta = redondear_dos_decimales(valor_normalizado - meta_normalizada)
    cumplida = (
        valor_normalizado <= meta_normalizada
        if sentido is SentidoMeta.MINIMIZAR
        else valor_normalizado >= meta_normalizada
    )
    desviacion_porcentual = (
        None
        if meta_normalizada == 0
        else redondear_dos_decimales(
            dividir_seguro(
                desviacion_absoluta,
                meta_normalizada,
                "meta",
            )
            * PORCENTAJE
        )
    )

    return ResultadoMetaAnual(
        valor_proyectado=valor_normalizado,
        meta=meta_normalizada,
        sentido=sentido,
        cumplida=cumplida,
        desviacion_absoluta=desviacion_absoluta,
        desviacion_porcentual=desviacion_porcentual,
    )
