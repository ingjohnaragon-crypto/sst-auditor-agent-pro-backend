"""Puerto de persistencia del borrador de acciones de mejora."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.accion_mejora import AccionMejora


class RepositorioAccionMejora(ABC):
    """Contrato de acceso a las acciones de un plan."""

    @abstractmethod
    async def listar_por_plan(self, plan_id: UUID) -> list[AccionMejora]:
        """Devuelve las acciones ya guardadas de ese plan."""

    @abstractmethod
    async def guardar(self, accion: AccionMejora) -> AccionMejora:
        """Inserta la acción. Si el estándar ya está, devuelve la fila existente."""
