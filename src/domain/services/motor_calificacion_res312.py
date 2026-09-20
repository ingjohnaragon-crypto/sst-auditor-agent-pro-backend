"""Motor de calificación Res. 0312: perfil empresarial y cumplimiento PHVA."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.exceptions.autoevaluacion import DatosEmpresaInvalidosError
from src.domain.models.autoevaluacion import (
    UMBRAL_PLAN_MEJORA,
    Autoevaluacion,
    CalificacionEstandar,
    ResultadoCalificacion,
)
from src.domain.models.empresa import NIVELES_RIESGO_ARL
from src.domain.models.estandar_minimo import EstandarMinimo
from src.domain.models.perfil_estandares import MapaPerfilEstandares
from src.domain.services.utilidades_matematicas import redondear_dos_decimales

CERO = Decimal("0")
CIEN = Decimal("100")


@dataclass(frozen=True, slots=True)
class CumplimientoFasePHVA:
    """Cumplimiento consolidado de una fase del ciclo PHVA."""

    ciclo_phva: str
    peso_maximo: Decimal
    puntaje_obtenido: Decimal
    porcentaje_cumplimiento: Decimal
    brecha: Decimal


@dataclass(frozen=True, slots=True)
class ResumenCumplimientoPHVA:
    """Resumen global y por fase del cumplimiento Res. 0312."""

    perfil: str
    puntaje_total: Decimal
    umbral_plan_mejora: Decimal
    requiere_plan_mejora: bool
    finalizada: bool
    fases: tuple[CumplimientoFasePHVA, ...]


def resolver_perfil_estandares(
    nivel_riesgo_arl: str,
    numero_trabajadores: int,
    mapa: MapaPerfilEstandares,
) -> str:
    """Resuelve el código de perfil según reglas versionadas en el mapa."""
    if numero_trabajadores <= 0:
        raise DatosEmpresaInvalidosError("El número de trabajadores debe ser mayor que 0")
    nivel = nivel_riesgo_arl.strip().upper()
    if nivel not in NIVELES_RIESGO_ARL:
        raise DatosEmpresaInvalidosError(
            f"El nivel de riesgo ARL debe ser uno de {', '.join(NIVELES_RIESGO_ARL)}"
        )
    return mapa.resolver(nivel, numero_trabajadores).codigo


def numerales_no_aplican(
    perfil: str,
    mapa: MapaPerfilEstandares,
) -> frozenset[str]:
    """Numerales Art. 27 no exigibles para el perfil (Art. 27 → NO_APLICA)."""
    return mapa.numerales_no_aplican(perfil)


def aplicar_no_aplica_faltantes(
    autoevaluacion: Autoevaluacion,
    estandares: list[EstandarMinimo],
    numerales_na: frozenset[str],
) -> None:
    """Autocompleta NO_APLICA solo en ítems aún sin calificación."""
    for estandar in estandares:
        if estandar.numeral not in numerales_na:
            continue
        if estandar.id in autoevaluacion.calificaciones:
            continue
        autoevaluacion.calificar(estandar, ResultadoCalificacion.NO_APLICA)


def orden_fases_efectivo(
    estandares: list[EstandarMinimo],
    orden_configurado: tuple[str, ...],
) -> tuple[str, ...]:
    """Orden del mapa (siempre) + fases del catálogo ausentes en el mapa al final."""
    presentes = {e.ciclo_phva.value for e in estandares}
    extras = sorted(presentes - set(orden_configurado))
    return tuple(orden_configurado) + tuple(extras)


def calcular_cumplimiento_phva(
    estandares: list[EstandarMinimo],
    calificaciones: dict[UUID, CalificacionEstandar],
    perfil: str,
    numerales_na: frozenset[str],
    orden_fases: tuple[str, ...],
    *,
    puntaje_total_persistido: Decimal | None,
    finalizada: bool,
) -> ResumenCumplimientoPHVA:
    """Agrega cumplimiento por fase PHVA (preview en vivo o finalizada)."""
    fases_orden = orden_fases_efectivo(estandares, orden_fases)
    por_fase: dict[str, list[EstandarMinimo]] = {fase: [] for fase in fases_orden}
    for estandar in estandares:
        clave = estandar.ciclo_phva.value
        if clave not in por_fase:
            por_fase[clave] = []
        por_fase[clave].append(estandar)

    fases: list[CumplimientoFasePHVA] = []
    puntaje_provisional = CERO
    for fase in fases_orden:
        items = por_fase.get(fase, [])
        peso_maximo = sum((e.valor_porcentual for e in items), start=CERO)
        obtenido = CERO
        for estandar in items:
            calificacion = calificaciones.get(estandar.id)
            if calificacion is not None:
                aporte = calificacion.puntaje
            elif estandar.numeral in numerales_na:
                aporte = estandar.valor_porcentual
            else:
                aporte = CERO
            obtenido += aporte
        if peso_maximo > CERO:
            porcentaje = redondear_dos_decimales((obtenido / peso_maximo) * CIEN)
        else:
            porcentaje = CERO
        fases.append(
            CumplimientoFasePHVA(
                ciclo_phva=fase,
                peso_maximo=redondear_dos_decimales(peso_maximo),
                puntaje_obtenido=redondear_dos_decimales(obtenido),
                porcentaje_cumplimiento=porcentaje,
                brecha=redondear_dos_decimales(peso_maximo - obtenido),
            )
        )
        puntaje_provisional += obtenido

    if finalizada and puntaje_total_persistido is not None:
        puntaje_total = redondear_dos_decimales(puntaje_total_persistido)
    else:
        puntaje_total = redondear_dos_decimales(puntaje_provisional)

    return ResumenCumplimientoPHVA(
        perfil=perfil,
        puntaje_total=puntaje_total,
        umbral_plan_mejora=UMBRAL_PLAN_MEJORA,
        requiere_plan_mejora=puntaje_total < UMBRAL_PLAN_MEJORA,
        finalizada=finalizada,
        fases=tuple(fases),
    )
