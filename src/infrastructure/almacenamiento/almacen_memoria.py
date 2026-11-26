"""Doble en memoria del puerto de almacenamiento (pruebas, sin red)."""


class AlmacenMemoria:
    """Implementa guardar / leer / eliminar sobre un dict[str, bytes]."""

    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}

    def guardar(self, relativa: str, contenido: bytes) -> None:
        """Publica el binario en la clave dada."""
        self.objetos[relativa] = contenido

    def leer(self, relativa: str) -> bytes:
        """Devuelve el binario. Si no existe, FileNotFoundError."""
        try:
            return self.objetos[relativa]
        except KeyError as exc:
            raise FileNotFoundError(relativa) from exc

    def eliminar(self, relativa: str) -> None:
        """Quita la clave si existe. No falla si ya no está."""
        self.objetos.pop(relativa, None)
