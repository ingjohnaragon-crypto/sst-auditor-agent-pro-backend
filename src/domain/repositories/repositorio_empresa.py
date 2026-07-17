"""Puerto de persistencia de `Empresa`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.empresa import Empresa


class RepositorioEmpresa(ABC):
    """Contrato de acceso a empresas — implementado en infraestructura."""

    @abstractmethod
    async def guardar(self, empresa: Empresa) -> Empresa:
        """Persiste o actualiza una empresa."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Empresa | None:
        """Busca por identificador."""

    @abstractmethod
    async def buscar_por_nit(self, nit: str) -> Empresa | None:
        """Busca por NIT (único)."""

    @abstractmethod
    async def listar(self) -> list[Empresa]:
        """Lista todas las empresas."""
