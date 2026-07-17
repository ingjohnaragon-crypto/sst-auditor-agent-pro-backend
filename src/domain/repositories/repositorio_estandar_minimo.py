"""Puerto de lectura del catálogo `estandares_minimos`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo


class RepositorioEstandarMinimo(ABC):
    """Contrato de acceso al catálogo de estándares mínimos."""

    @abstractmethod
    async def listar(self, ciclo_phva: CicloPHVA | None = None) -> list[EstandarMinimo]:
        """Lista el catálogo, opcionalmente filtrado por ciclo PHVA."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> EstandarMinimo | None:
        """Busca un ítem por identificador."""

    @abstractmethod
    async def contar(self) -> int:
        """Total de ítems del catálogo (regla de finalización)."""
