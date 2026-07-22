"""Puerto de persistencia de `ControlRiesgo`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.control_riesgo import ControlRiesgo


class RepositorioControlRiesgo(ABC):
    """Contrato de persistencia de controles."""

    @abstractmethod
    async def guardar(self, control: ControlRiesgo) -> ControlRiesgo:
        """Persiste o actualiza un control."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> ControlRiesgo | None:
        """Busca por id o None."""

    @abstractmethod
    async def listar_por_evaluacion(self, evaluacion_riesgo_id: UUID) -> list[ControlRiesgo]:
        """Lista controles de una evaluación."""

    @abstractmethod
    async def eliminar(self, id: UUID) -> bool:
        """Elimina por id. True si existía."""
