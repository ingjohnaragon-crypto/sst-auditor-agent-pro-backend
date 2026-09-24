"""Metadatos de un documento de soporte — sin el binario."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID

from src.domain.exceptions.evidencia import EvidenciaInvalidaError, EvidenciaYaInactivaError

TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024
MIME_EXTENSIONES: dict[str, frozenset[str]] = {
    "application/pdf": frozenset({".pdf"}),
    "image/jpeg": frozenset({".jpg", ".jpeg"}),
    "image/png": frozenset({".png"}),
}
ESQUEMAS_PROHIBIDOS = ("http://", "https://", "file://", "file:")


@dataclass
class Evidencia:
    """Ubicación y atributos de un adjunto ligado a una calificación."""

    id: UUID | None
    calificacion_estandar_id: UUID
    usuario_id: UUID
    nombre_archivo: str
    tipo_mime: str
    tamano_bytes: int
    ruta_almacenamiento: str
    fecha_carga: datetime
    activo: bool = True
    fecha_eliminacion: datetime | None = None
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        calificacion_estandar_id: UUID,
        usuario_id: UUID,
        nombre_archivo: str,
        tipo_mime: str,
        tamano_bytes: int,
        ruta_almacenamiento: str,
    ) -> "Evidencia":
        """Valida tipo, tamaño y ruta antes de construir el metadato."""
        nombre = _validar_nombre(nombre_archivo)
        mime = _validar_mime_y_extension(nombre, tipo_mime)
        tamano = _validar_tamano(tamano_bytes)
        ruta = _validar_ruta(ruta_almacenamiento)
        ahora = datetime.now(UTC)
        return cls(
            id=None,
            calificacion_estandar_id=calificacion_estandar_id,
            usuario_id=usuario_id,
            nombre_archivo=nombre,
            tipo_mime=mime,
            tamano_bytes=tamano,
            ruta_almacenamiento=ruta,
            fecha_carga=ahora,
            activo=True,
            fecha_eliminacion=None,
            fecha_creacion=ahora,
            fecha_actualizacion=ahora,
        )

    def dar_de_baja(self) -> None:
        """Borrado lógico. Conserva la fila (D. 1072, conservación documental)."""
        if not self.activo:
            raise EvidenciaYaInactivaError()
        ahora = datetime.now(UTC)
        self.activo = False
        self.fecha_eliminacion = ahora
        self.fecha_actualizacion = ahora


def _validar_nombre(nombre_archivo: str) -> str:
    nombre = nombre_archivo.strip()
    if not nombre or len(nombre) > 255:
        raise EvidenciaInvalidaError(
            "El nombre del archivo es obligatorio y máximo de 255 caracteres"
        )
    if "/" in nombre or "\\" in nombre:
        raise EvidenciaInvalidaError("El nombre del archivo no puede incluir una ruta")
    return nombre


def _validar_mime_y_extension(nombre: str, tipo_mime: str) -> str:
    mime = tipo_mime.strip().lower()
    extensiones = MIME_EXTENSIONES.get(mime)
    if extensiones is None:
        raise EvidenciaInvalidaError("El tipo de archivo no está permitido")
    sufijo = PurePosixPath(nombre.lower()).suffix
    if sufijo not in extensiones:
        raise EvidenciaInvalidaError("La extensión no coincide con el tipo MIME")
    return mime


def _validar_tamano(tamano_bytes: int) -> int:
    if tamano_bytes <= 0 or tamano_bytes > TAMANO_MAXIMO_BYTES:
        raise EvidenciaInvalidaError("El tamaño debe ser mayor que 0 y no superar 10 MiB")
    return tamano_bytes


def _validar_ruta(ruta_almacenamiento: str) -> str:
    ruta = ruta_almacenamiento.strip().replace("\\", "/")
    if not ruta:
        raise EvidenciaInvalidaError("La ruta de almacenamiento es obligatoria")
    minuscula = ruta.lower()
    if any(minuscula.startswith(esquema) for esquema in ESQUEMAS_PROHIBIDOS):
        raise EvidenciaInvalidaError("La ruta debe ser relativa, sin esquema")
    if ruta.startswith("/") or ":" in ruta or ".." in PurePosixPath(ruta).parts:
        raise EvidenciaInvalidaError("La ruta no puede ser absoluta ni subir de directorio")
    if len(ruta) > 500:
        raise EvidenciaInvalidaError("La ruta de almacenamiento supera 500 caracteres")
    return ruta
