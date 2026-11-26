"""Puerto de persistencia de metadatos de archivos documentales."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.archivo_documental import ArchivoDocumental


class RepositorioArchivoDocumental(ABC):
    """Contrato de acceso a archivos documentales. No devuelve filas ORM."""

    @abstractmethod
    async def guardar(self, archivo: ArchivoDocumental) -> ArchivoDocumental:
        """Inserta el metadato y asigna id si venía None."""

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: UUID) -> list[ArchivoDocumental]:
        """Lista por empresa, más recientes primero."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> ArchivoDocumental | None:
        """Carga un archivo por id o None."""

    @abstractmethod
    async def eliminar(self, id: UUID) -> None:
        """Borrado físico de la fila. Idempotente si ya no existe."""

    @abstractmethod
    async def existe_empresa(self, empresa_id: UUID) -> bool:
        """Indica si la empresa existe."""
