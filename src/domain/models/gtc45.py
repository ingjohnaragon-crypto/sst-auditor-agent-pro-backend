"""Constantes y enums de dominio para GTC 45 (Anexo A / tabla de peligros)."""

from enum import StrEnum

ND_VALIDOS: frozenset[int] = frozenset({10, 6, 2, 0})
NE_VALIDOS: frozenset[int] = frozenset({4, 3, 2, 1})
NC_VALIDOS: frozenset[int] = frozenset({100, 60, 25, 10})


class ClasificacionPeligro(StrEnum):
    BIOLOGICO = "BIOLOGICO"
    FISICO = "FISICO"
    QUIMICO = "QUIMICO"
    PSICOSOCIAL = "PSICOSOCIAL"
    BIOMECANICO = "BIOMECANICO"
    CONDICIONES_SEGURIDAD = "CONDICIONES_SEGURIDAD"
    FENOMENOS_NATURALES = "FENOMENOS_NATURALES"


class TipoControl(StrEnum):
    ELIMINACION = "ELIMINACION"
    SUSTITUCION = "SUSTITUCION"
    INGENIERIA = "INGENIERIA"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    EPP = "EPP"


class InterpretacionNR(StrEnum):
    I = "I"  # noqa: E741 — rótulo normativo de la tabla A.3
    II = "II"
    III = "III"
    IV = "IV"


class AceptabilidadRiesgo(StrEnum):
    NO_ACEPTABLE = "NO_ACEPTABLE"
    ACEPTABLE_CON_CONTROL = "ACEPTABLE_CON_CONTROL"
    MEJORABLE = "MEJORABLE"
    ACEPTABLE = "ACEPTABLE"


ACEPTABILIDAD_POR_INTERPRETACION: dict[InterpretacionNR, AceptabilidadRiesgo] = {
    InterpretacionNR.I: AceptabilidadRiesgo.NO_ACEPTABLE,
    InterpretacionNR.II: AceptabilidadRiesgo.ACEPTABLE_CON_CONTROL,
    InterpretacionNR.III: AceptabilidadRiesgo.MEJORABLE,
    InterpretacionNR.IV: AceptabilidadRiesgo.ACEPTABLE,
}
