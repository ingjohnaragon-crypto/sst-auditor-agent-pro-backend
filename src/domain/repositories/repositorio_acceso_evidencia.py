"""Puerto de persistencia de la auditoría de descargas."""

from abc import ABC, abstractmethod

from src.domain.models.acceso_evidencia import AccesoEvidencia


class RepositorioAccesoEvidencia(ABC):
    """Contrato de escritura de accesos. No devuelve filas ORM."""

    @abstractmethod
    async def guardar(self, acceso: AccesoEvidencia) -> AccesoEvidencia:
        """Inserta el intento de descarga."""
