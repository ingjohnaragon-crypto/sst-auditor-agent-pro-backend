"""Carga del mapa de perfiles Res. 0312 desde JSON versionado."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.domain.models.perfil_estandares import MapaPerfilEstandares

_RAIZ_REPO = Path(__file__).resolve().parents[3]
RUTA_MAPA_PERFIL_POR_DEFECTO = _RAIZ_REPO / "scripts" / "datos" / "perfil_estandares_res312.json"


def _cargar_dict(ruta: Path) -> dict[str, Any]:
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el mapa de perfiles Res. 0312: {ruta}")
    payload = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("El mapa de perfiles debe ser un objeto JSON")
    return payload


@lru_cache(maxsize=1)
def cargar_mapa_perfil_estandares(
    ruta: str | None = None,
) -> MapaPerfilEstandares:
    """Carga (y cachea) el mapa de numerales no aplicables por perfil."""
    path = Path(ruta) if ruta else RUTA_MAPA_PERFIL_POR_DEFECTO
    return MapaPerfilEstandares.desde_dict(_cargar_dict(path))
