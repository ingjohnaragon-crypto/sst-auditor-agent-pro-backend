"""Entidad de lectura del catálogo `estandares_minimos` (Res. 0312)."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class CicloPHVA(StrEnum):
    """Fases del ciclo PHVA del SG-SST."""

    PLANEAR = "PLANEAR"
    HACER = "HACER"
    VERIFICAR = "VERIFICAR"
    ACTUAR = "ACTUAR"


@dataclass(frozen=True)
class EstandarMinimo:
    """Ítem del catálogo de estándares mínimos — solo lectura desde dominio."""

    id: UUID
    ciclo_phva: CicloPHVA
    numeral: str
    descripcion: str
    valor_porcentual: Decimal
