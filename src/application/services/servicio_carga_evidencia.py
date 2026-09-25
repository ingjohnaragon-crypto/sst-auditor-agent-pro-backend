"""Carga el binario de una evidencia y persiste sus metadatos."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID, uuid4

from src.application.dto.respuesta_evidencia import RespuestaEvidencia
from src.application.mappers.mapper_evidencia import MapperEvidencia
from src.domain.exceptions.evidencia import (
    AlmacenamientoNoConfiguradoError,
    CalificacionNoEncontradaError,
    EvidenciaInvalidaError,
)
from src.domain.models.evidencia import MIME_EXTENSIONES, TAMANO_MAXIMO_BYTES, Evidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia

TAMANO_BLOQUE = 64 * 1024
MAGIC: dict[str, bytes] = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG",
}
EXTENSION_POR_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class AlmacenEvidencias(Protocol):
    """Puerto de escritura. La implementación vive en infraestructura."""

    def guardar(self, relativa: str, contenido: bytes) -> None:
        """Publica el binario en la ruta relativa."""

    def eliminar(self, relativa: str) -> None:
        """Quita un archivo que no llegó a confirmarse."""


class ServicioCargaEvidencia:
    """Valida contenido, escribe en la raíz y crea la fila. Limpia si la fila falla."""

    def __init__(
        self,
        repositorio: RepositorioEvidencia,
        almacen: AlmacenEvidencias,
        *,
        raiz_configurada: bool,
    ) -> None:
        self._repositorio = repositorio
        self._almacen = almacen
        self._raiz_configurada = raiz_configurada

    async def cargar(
        self,
        calificacion_id: UUID,
        nombre: str,
        tipo_mime: str,
        contenido: bytes,
        usuario_id: UUID,
    ) -> RespuestaEvidencia:
        """Persiste metadatos medidos por el servidor y el binario bajo la raíz."""
        if not self._raiz_configurada:
            raise AlmacenamientoNoConfiguradoError()
        if not await self._repositorio.existe_calificacion(calificacion_id):
            raise CalificacionNoEncontradaError()
        _exigir_tope(contenido)
        mime = tipo_mime.strip().lower()
        _exigir_magic(mime, contenido)
        extension = EXTENSION_POR_MIME.get(mime, "")
        ruta = f"evidencias/{calificacion_id}/{uuid4()}{extension}"
        evidencia = Evidencia.crear(
            calificacion_estandar_id=calificacion_id,
            usuario_id=usuario_id,
            nombre_archivo=nombre,
            tipo_mime=mime,
            tamano_bytes=len(contenido),
            ruta_almacenamiento=ruta,
        )
        self._almacen.guardar(ruta, contenido)
        try:
            guardada = await self._repositorio.guardar(evidencia)
        except Exception:
            self._almacen.eliminar(ruta)
            raise
        return MapperEvidencia.a_respuesta(guardada)


def leer_con_tope(bloques: Iterable[bytes], tope: int = TAMANO_MAXIMO_BYTES) -> bytes:
    """Concatena bloques y corta si la suma supera el tope."""
    piezas: list[bytes] = []
    total = 0
    for bloque in bloques:
        total += len(bloque)
        if total > tope:
            raise EvidenciaInvalidaError("El tamaño debe ser mayor que 0 y no superar 10 MiB")
        piezas.append(bloque)
    return b"".join(piezas)


def _exigir_tope(contenido: bytes) -> None:
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise EvidenciaInvalidaError("El tamaño debe ser mayor que 0 y no superar 10 MiB")


def _exigir_magic(mime: str, contenido: bytes) -> None:
    if mime not in MIME_EXTENSIONES:
        raise EvidenciaInvalidaError("El tipo de archivo no está permitido")
    firma = MAGIC.get(mime)
    if firma is None or not contenido.startswith(firma):
        raise EvidenciaInvalidaError("El contenido no coincide con el tipo de archivo")
