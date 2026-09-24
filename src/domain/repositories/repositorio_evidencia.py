"""Puerto de persistencia de metadatos de evidencias."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.evidencia import Evidencia


class RepositorioEvidencia(ABC):
    """Contrato de acceso a evidencias. No devuelve filas ORM."""

    @abstractmethod
    async def guardar(self, evidencia: Evidencia) -> Evidencia:
        """Inserta o actualiza el metadato."""

    @abstractmethod
    async def listar_activas_por_calificacion(
        self, calificacion_estandar_id: UUID
    ) -> list[Evidencia]:
        """Lista solo evidencias con `activo=true`."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Evidencia | None:
        """Carga una evidencia, activa o no."""

    @abstractmethod
    async def existe_calificacion(self, calificacion_estandar_id: UUID) -> bool:
        """Indica si la calificación del estándar existe."""
