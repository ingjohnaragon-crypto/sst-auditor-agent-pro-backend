"""Puerto del dominio: emisión y validación de tokens (implementado en infraestructura)."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.usuario import Usuario

TIPO_TOKEN_DESCARGA = "descarga"


class ServicioTokens(ABC):
    """Contrato de emisión/validación de tokens de acceso y de refresco."""

    @abstractmethod
    def emitir_token_acceso(self, usuario: Usuario) -> str:
        """Emite el token de acceso del usuario (incluye su rol)."""

    @abstractmethod
    def emitir_token_refresco(self, usuario: Usuario) -> str:
        """Emite el token de refresco del usuario (sin rol; no da acceso a recursos)."""

    @abstractmethod
    def emitir_token_descarga(self, usuario_id: UUID, evidencia_id: UUID, segundos: int) -> str:
        """Emite un JWT de vida corta para descargar una evidencia. No otorga sesión."""

    @abstractmethod
    def decodificar(self, token: str) -> dict[str, object]:
        """Devuelve los claims del token.

        Lanza `TokenExpiradoException` si venció y `TokenInvalidoException` si la
        firma o la estructura no son válidas.
        """
