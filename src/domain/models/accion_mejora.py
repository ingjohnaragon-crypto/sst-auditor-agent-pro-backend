"""Borrador de acción de mejora ligado a un ítem en NO_CUMPLE."""

from dataclasses import dataclass
from uuid import UUID

from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo


@dataclass
class AccionMejora:
    """Acción generada desde un incumplimiento. El responsable nace vacío."""

    id: UUID | None
    plan_id: UUID
    estandar_id: UUID
    ciclo_phva: CicloPHVA
    responsable_sugerido: str | None

    @classmethod
    def crear(cls, plan_id: UUID, estandar: EstandarMinimo) -> "AccionMejora":
        """Copia el ítem y su ciclo. No asigna responsable."""
        return cls(
            id=None,
            plan_id=plan_id,
            estandar_id=estandar.id,
            ciclo_phva=estandar.ciclo_phva,
            responsable_sugerido=None,
        )
