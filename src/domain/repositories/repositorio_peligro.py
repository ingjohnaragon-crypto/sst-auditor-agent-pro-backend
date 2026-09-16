"""Puerto de persistencia de `Peligro`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.peligro import Peligro


class RepositorioPeligro(ABC):
    """Contrato de persistencia — implementaciones en infrastructure/."""

    @abstractmethod
    async def guardar(self, peligro: Peligro) -> Peligro:
        """Persiste o actualiza un peligro."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Peligro | None:
        """Busca por id o None."""

    @abstractmethod
    async def listar_por_proceso(self, proceso_actividad_id: UUID) -> list[Peligro]:
        """Lista peligros de un proceso."""

    @abstractmethod
    async def eliminar(self, id: UUID) -> bool:
        """Elimina por id (cascade a evaluación/controles). True si existía."""
