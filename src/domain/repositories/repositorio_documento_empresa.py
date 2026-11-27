"""Puerto de documentos de empresa del catálogo PHVA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.documento_empresa import DocumentoEmpresa


class RepositorioDocumentoEmpresa(ABC):
    """Persistencia de documentos vigentes por empresa y tipo."""

    @abstractmethod
    async def existe_empresa(self, empresa_id: UUID) -> bool:
        """True si la empresa existe."""

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: UUID) -> list[DocumentoEmpresa]:
        """Filas existentes de la empresa (puede no cubrir todos los tipos)."""

    @abstractmethod
    async def buscar_por_empresa_y_tipo(
        self, empresa_id: UUID, tipo_id: UUID
    ) -> DocumentoEmpresa | None:
        """Documento vigente o None."""

    @abstractmethod
    async def guardar(self, documento: DocumentoEmpresa) -> DocumentoEmpresa:
        """Inserta o actualiza el vigente empresa+tipo."""
