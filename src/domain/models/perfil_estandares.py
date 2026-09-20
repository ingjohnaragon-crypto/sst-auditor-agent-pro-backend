"""Perfiles Res. 0312 versionados en datos (sin enum cerrado de tablas)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.models.empresa import NIVELES_RIESGO_ARL
from src.domain.models.estandar_minimo import CicloPHVA


@dataclass(frozen=True, slots=True)
class ReglaPerfilEstandares:
    """Criterio de matching por tamaño y riesgo ARL."""

    min_trabajadores: int | None
    max_trabajadores: int | None
    riesgos: frozenset[str] | None
    es_fallback: bool

    def coincide(self, nivel_riesgo_arl: str, numero_trabajadores: int) -> bool:
        """True si la empresa encaja en esta regla (el fallback nunca coincide aquí)."""
        if self.es_fallback:
            return False
        if self.min_trabajadores is not None and numero_trabajadores < self.min_trabajadores:
            return False
        if self.max_trabajadores is not None and numero_trabajadores > self.max_trabajadores:
            return False
        if self.riesgos is not None and nivel_riesgo_arl not in self.riesgos:
            return False
        return True


@dataclass(frozen=True, slots=True)
class DefinicionPerfilEstandares:
    """Un perfil de exigibilidad (p. ej. TABLA_7) con su regla y numerales NA."""

    codigo: str
    articulo: int | None
    prioridad: int
    regla: ReglaPerfilEstandares
    numerales_no_aplican: frozenset[str]


@dataclass(frozen=True, slots=True)
class MapaPerfilEstandares:
    """Catálogo de perfiles + orden PHVA; extensible sin cambiar el motor."""

    perfiles: tuple[DefinicionPerfilEstandares, ...]
    orden_fases_phva: tuple[str, ...]
    _por_codigo: dict[str, DefinicionPerfilEstandares]

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> MapaPerfilEstandares:
        """Construye el mapa desde JSON versionado."""
        orden_raw = datos.get("orden_fases_phva")
        if not isinstance(orden_raw, list) or not orden_raw:
            raise ValueError("Se requiere 'orden_fases_phva' como lista no vacía")
        orden: list[str] = []
        for fase in orden_raw:
            if not isinstance(fase, str) or not fase.strip():
                raise ValueError(f"Fase PHVA inválida: {fase!r}")
            codigo_fase = fase.strip().upper()
            try:
                CicloPHVA(codigo_fase)
            except ValueError as exc:
                raise ValueError(
                    f"Fase PHVA '{codigo_fase}' no está en CicloPHVA; "
                    "amplía el enum del dominio al actualizar la norma"
                ) from exc
            orden.append(codigo_fase)

        perfiles_raw = datos.get("perfiles")
        if not isinstance(perfiles_raw, dict) or not perfiles_raw:
            raise ValueError("El mapa de perfiles requiere la clave 'perfiles'")

        definiciones: list[DefinicionPerfilEstandares] = []
        for codigo, entrada in perfiles_raw.items():
            if not isinstance(codigo, str) or not codigo.strip():
                raise ValueError(f"Código de perfil inválido: {codigo!r}")
            if not isinstance(entrada, dict):
                raise ValueError(f"La entrada de perfil '{codigo}' debe ser un objeto")
            definiciones.append(_parsear_definicion(codigo.strip(), entrada))

        if not any(d.regla.es_fallback for d in definiciones):
            raise ValueError("Debe existir al menos un perfil con regla.fallback=true")

        ordenados = tuple(sorted(definiciones, key=lambda d: d.prioridad))
        por_codigo = {d.codigo: d for d in ordenados}
        return cls(
            perfiles=ordenados,
            orden_fases_phva=tuple(orden),
            _por_codigo=por_codigo,
        )

    def numerales_no_aplican(self, codigo_perfil: str) -> frozenset[str]:
        """Numerales Art. 27 no exigibles para el código de perfil."""
        definicion = self._por_codigo.get(codigo_perfil)
        if definicion is None:
            raise KeyError(f"Perfil desconocido: {codigo_perfil}")
        return definicion.numerales_no_aplican

    def resolver(
        self, nivel_riesgo_arl: str, numero_trabajadores: int
    ) -> DefinicionPerfilEstandares:
        """Primera regla no-fallback que coincida; si ninguna, el fallback."""
        for definicion in self.perfiles:
            if definicion.regla.coincide(nivel_riesgo_arl, numero_trabajadores):
                return definicion
        for definicion in self.perfiles:
            if definicion.regla.es_fallback:
                return definicion
        raise RuntimeError("Mapa de perfiles sin fallback (invariante violado)")


def _parsear_definicion(codigo: str, entrada: dict[str, Any]) -> DefinicionPerfilEstandares:
    articulo = entrada.get("articulo")
    if articulo is not None and not isinstance(articulo, int):
        raise ValueError(f"'articulo' de '{codigo}' debe ser entero o ausente")

    prioridad = entrada.get("prioridad", 100)
    if not isinstance(prioridad, int):
        raise ValueError(f"'prioridad' de '{codigo}' debe ser entero")

    regla_raw = entrada.get("regla")
    if not isinstance(regla_raw, dict):
        raise ValueError(f"El perfil '{codigo}' requiere objeto 'regla'")

    es_fallback = bool(regla_raw.get("fallback", False))
    min_t = regla_raw.get("min_trabajadores")
    max_t = regla_raw.get("max_trabajadores")
    riesgos_raw = regla_raw.get("riesgos")

    if not es_fallback:
        if min_t is not None and not isinstance(min_t, int):
            raise ValueError(f"'min_trabajadores' inválido en '{codigo}'")
        if max_t is not None and not isinstance(max_t, int):
            raise ValueError(f"'max_trabajadores' inválido en '{codigo}'")
        if riesgos_raw is not None:
            if not isinstance(riesgos_raw, list) or not riesgos_raw:
                raise ValueError(f"'riesgos' de '{codigo}' debe ser lista no vacía")
            riesgos_set = frozenset(str(r).strip().upper() for r in riesgos_raw)
            desconocidos = riesgos_set - frozenset(NIVELES_RIESGO_ARL)
            if desconocidos:
                raise ValueError(f"Riesgos desconocidos en '{codigo}': {sorted(desconocidos)}")
            riesgos: frozenset[str] | None = riesgos_set
        else:
            riesgos = None
    else:
        min_t = None
        max_t = None
        riesgos = None

    numerales = entrada.get("numerales_no_aplican", [])
    if not isinstance(numerales, list):
        raise ValueError(f"'numerales_no_aplican' de '{codigo}' debe ser una lista")
    limpios: list[str] = []
    for numeral in numerales:
        if not isinstance(numeral, str) or not numeral.strip():
            raise ValueError(f"Numeral inválido en perfil '{codigo}': {numeral!r}")
        limpios.append(numeral.strip())

    return DefinicionPerfilEstandares(
        codigo=codigo,
        articulo=articulo,
        prioridad=prioridad,
        regla=ReglaPerfilEstandares(
            min_trabajadores=min_t if isinstance(min_t, int) else None,
            max_trabajadores=max_t if isinstance(max_t, int) else None,
            riesgos=riesgos,
            es_fallback=es_fallback,
        ),
        numerales_no_aplican=frozenset(limpios),
    )
