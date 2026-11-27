"""Puerto del catálogo de tipos documentales PHVA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.tipo_documento_sst import TipoDocumentoSst


class RepositorioTipoDocumentoSst(ABC):
    """Acceso de solo lectura (y semilla) al catálogo de tipos."""

    @abstractmethod
    async def listar(self) -> list[TipoDocumentoSst]:
        """Todos los tipos ordenados por fase y nombre."""

    @abstractmethod
    async def buscar_por_id(self, tipo_id: UUID) -> TipoDocumentoSst | None:
        """Tipo por id o None."""

    @abstractmethod
    async def listar_estandares_por_tipo(self, tipo_id: UUID) -> list[UUID]:
        """Ids de estándares 0312 vinculados al tipo (puede ser vacío)."""

    @abstractmethod
    async def mapear_estandares_por_tipos(self, tipo_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        """Mapa tipo_id → estandares_ids en una sola consulta (vacío si no hay ids)."""
