"""Puerto de persistencia del agregado `PlanMejora`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.plan_mejora import PlanMejora


class RepositorioPlanMejora(ABC):
    """Contrato de acceso al plan de mejora y sus actividades."""

    @abstractmethod
    async def guardar(self, plan: PlanMejora) -> PlanMejora:
        """Inserta o reemplaza actividades y meses en una transacción."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> PlanMejora | None:
        """Carga el plan con sus actividades."""

    @abstractmethod
    async def buscar_por_autoevaluacion(self, autoevaluacion_id: UUID) -> PlanMejora | None:
        """Devuelve el único plan de esa autoevaluación, si existe."""

    @abstractmethod
    async def eliminar(self, id: UUID) -> None:
        """Borra el plan. Si no existe, no hace nada."""
