"""Puerto del dominio: hashing de contraseñas (implementado en infraestructura)."""

from abc import ABC, abstractmethod


class ServicioHashContrasena(ABC):
    """Contrato de cifrado de contraseñas — la contraseña en claro nunca se persiste."""

    @abstractmethod
    async def generar_hash(self, contrasena: str) -> str:
        """Genera el hash (con salt propio) de la contraseña en claro."""

    @abstractmethod
    async def verificar(self, contrasena: str, hash_contrasena: str) -> bool:
        """Comprueba si la contraseña en claro corresponde al hash almacenado."""
