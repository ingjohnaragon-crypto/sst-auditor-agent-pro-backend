"""Puerto de persistencia de `EvaluacionRiesgo`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo


class RepositorioEvaluacionRiesgo(ABC):
    """Contrato de persistencia — 1 evaluación vigente por peligro."""

    @abstractmethod
    async def guardar(self, evaluacion: EvaluacionRiesgo) -> EvaluacionRiesgo:
        """Inserta o actualiza la evaluación (upsert por peligro_id)."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> EvaluacionRiesgo | None:
        """Busca por id o None."""

    @abstractmethod
    async def buscar_por_peligro(self, peligro_id: UUID) -> EvaluacionRiesgo | None:
        """Busca la evaluación vigente del peligro."""
