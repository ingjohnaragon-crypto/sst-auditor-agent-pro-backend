"""Puerto de persistencia del agregado `Autoevaluacion`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.autoevaluacion import Autoevaluacion


class RepositorioAutoevaluacion(ABC):
    """Contrato de acceso a autoevaluaciones con calificaciones embebidas."""

    @abstractmethod
    async def guardar(self, autoevaluacion: Autoevaluacion) -> Autoevaluacion:
        """Persiste el agregado completo (upsert de calificaciones) en una transacción."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Autoevaluacion | None:
        """Carga la autoevaluación con sus calificaciones."""

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: UUID) -> list[Autoevaluacion]:
        """Histórico de autoevaluaciones de una empresa (fecha desc)."""
