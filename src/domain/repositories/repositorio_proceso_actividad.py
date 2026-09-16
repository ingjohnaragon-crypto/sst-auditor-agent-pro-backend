"""Puerto de persistencia de `ProcesoActividad`."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.matriz_nodos import NodoProcesoMatriz
from src.domain.models.proceso_actividad import ProcesoActividad


class RepositorioProcesoActividad(ABC):
    """Contrato de persistencia — implementaciones en infrastructure/."""

    @abstractmethod
    async def guardar(self, proceso: ProcesoActividad) -> ProcesoActividad:
        """Persiste o actualiza un proceso."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> ProcesoActividad | None:
        """Busca por id o None."""

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: UUID) -> list[ProcesoActividad]:
        """Lista procesos de una empresa ordenados por nombre."""

    @abstractmethod
    async def eliminar(self, id: UUID) -> bool:
        """Elimina por id (cascade a peligros). True si existía."""

    @abstractmethod
    async def obtener_matriz_por_empresa(self, empresa_id: UUID) -> list[NodoProcesoMatriz]:
        """Carga la matriz jerárquica procesos→peligros→evaluación→controles."""
