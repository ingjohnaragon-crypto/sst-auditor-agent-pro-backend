"""Puerto del dominio: repositorio de usuarios (implementado en infraestructura)."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.usuario import Usuario


class RepositorioUsuario(ABC):
    """Contrato de persistencia de `Usuario` — devuelve entidades de dominio, nunca ORM."""

    @abstractmethod
    async def buscar_por_correo(self, correo: str) -> Usuario | None:
        """Busca un usuario por su correo (ya normalizado a minúsculas)."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Busca un usuario por su identificador."""

    @abstractmethod
    async def guardar(self, usuario: Usuario) -> Usuario:
        """Persiste el usuario y devuelve la entidad con id y fechas asignados."""

    @abstractmethod
    async def existe_por_correo(self, correo: str) -> bool:
        """Indica si ya existe un usuario con el correo dado."""
