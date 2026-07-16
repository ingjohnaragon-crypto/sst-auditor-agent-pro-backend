"""Puerto del dominio: emisión y validación de tokens (implementado en infraestructura)."""

from abc import ABC, abstractmethod

from src.domain.models.usuario import Usuario


class ServicioTokens(ABC):
    """Contrato de emisión/validación de tokens de acceso y de refresco."""

    @abstractmethod
    def emitir_token_acceso(self, usuario: Usuario) -> str:
        """Emite el token de acceso del usuario (incluye su rol)."""

    @abstractmethod
    def emitir_token_refresco(self, usuario: Usuario) -> str:
        """Emite el token de refresco del usuario (sin rol; no da acceso a recursos)."""

    @abstractmethod
    def decodificar(self, token: str) -> dict[str, object]:
        """Devuelve los claims del token.

        Lanza `TokenExpiradoException` si venció y `TokenInvalidoException` si la
        firma o la estructura no son válidas.
        """
