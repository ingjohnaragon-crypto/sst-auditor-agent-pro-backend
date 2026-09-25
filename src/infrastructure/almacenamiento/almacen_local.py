"""Escritura de binarios bajo una raíz local, sin salir de ese directorio."""

from pathlib import Path


class AlmacenLocal:
    """Guarda y borra rutas relativas contenidas en la raíz."""

    def __init__(self, raiz: Path | None) -> None:
        self._raiz = raiz

    def guardar(self, relativa: str, contenido: bytes) -> None:
        """Crea el directorio padre y escribe el archivo."""
        destino = self._destino(relativa)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)

    def eliminar(self, relativa: str) -> None:
        """Borra el archivo si existe. No falla si ya no está."""
        destino = self._destino(relativa)
        if destino.is_file():
            destino.unlink()

    def _destino(self, relativa: str) -> Path:
        if self._raiz is None:
            msg = "No hay raíz de almacenamiento"
            raise ValueError(msg)
        raiz = self._raiz.resolve()
        candidata = (raiz / relativa).resolve()
        candidata.relative_to(raiz)
        return candidata
