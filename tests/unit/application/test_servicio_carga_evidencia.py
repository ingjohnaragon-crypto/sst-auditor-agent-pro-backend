"""Pruebas de la carga de binarios de evidencia."""

from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.services.servicio_carga_evidencia import (
    ServicioCargaEvidencia,
    leer_con_tope,
)
from src.domain.exceptions.evidencia import (
    AlmacenamientoNoConfiguradoError,
    CalificacionNoEncontradaError,
    EvidenciaInvalidaError,
)
from src.domain.models.evidencia import TAMANO_MAXIMO_BYTES, Evidencia

PDF = b"%PDF-1.4"
PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff\xe0"


class _Almacen:
    def __init__(self) -> None:
        self.guardados: dict[str, bytes] = {}

    def guardar(self, relativa: str, contenido: bytes) -> None:
        self.guardados[relativa] = contenido

    def eliminar(self, relativa: str) -> None:
        self.guardados.pop(relativa, None)


def _servicio(
    *,
    existe: bool = True,
    raiz: bool = True,
    falla_guardar: bool = False,
) -> tuple[ServicioCargaEvidencia, _Almacen, AsyncMock]:
    repositorio = AsyncMock()
    repositorio.existe_calificacion.return_value = existe

    async def _guardar(evidencia: Evidencia) -> Evidencia:
        if falla_guardar:
            raise RuntimeError("db")
        evidencia.id = uuid4()
        return evidencia

    repositorio.guardar.side_effect = _guardar
    almacen = _Almacen()
    servicio = ServicioCargaEvidencia(
        repositorio=repositorio,
        almacen=almacen,
        raiz_configurada=raiz,
    )
    return servicio, almacen, repositorio


@pytest.mark.asyncio
async def test_should_guardar_pdf_bajo_la_calificacion() -> None:
    calificacion_id = uuid4()
    usuario_id = uuid4()
    servicio, almacen, _repo = _servicio()

    respuesta = await servicio.cargar(
        calificacion_id, "acta.pdf", "application/pdf", PDF, usuario_id
    )

    assert respuesta.usuario_id == usuario_id
    assert respuesta.tamano_bytes == len(PDF)
    assert str(respuesta.ruta_almacenamiento).startswith(f"evidencias/{calificacion_id}/")
    assert len(almacen.guardados) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("nombre", "mime", "contenido"),
    [
        ("foto.jpg", "image/jpeg", JPEG),
        ("foto.jpeg", "image/jpeg", JPEG),
        ("plano.png", "image/png", PNG),
    ],
)
async def test_should_aceptar_imagen_valida(nombre: str, mime: str, contenido: bytes) -> None:
    servicio, almacen, _repo = _servicio()
    await servicio.cargar(uuid4(), nombre, mime, contenido, uuid4())
    assert len(almacen.guardados) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("nombre", "mime", "contenido"),
    [
        ("acta.pdf", "application/pdf", PNG),
        ("nota.html", "text/html", b"<html>"),
        ("virus.exe", "application/octet-stream", b"MZ"),
    ],
)
async def test_should_rechazar_magic_o_tipo(nombre: str, mime: str, contenido: bytes) -> None:
    servicio, almacen, _repo = _servicio()
    with pytest.raises(EvidenciaInvalidaError):
        await servicio.cargar(uuid4(), nombre, mime, contenido, uuid4())
    assert almacen.guardados == {}


@pytest.mark.asyncio
async def test_should_rechazar_when_supera_10_mib() -> None:
    servicio, almacen, _repo = _servicio()
    grande = b"%PDF" + b"a" * TAMANO_MAXIMO_BYTES
    with pytest.raises(EvidenciaInvalidaError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", grande, uuid4())
    assert almacen.guardados == {}


def test_should_cortar_lectura_when_bloques_superan_el_tope() -> None:
    bloques = [b"a" * (TAMANO_MAXIMO_BYTES // 2 + 1) for _ in range(3)]
    with pytest.raises(EvidenciaInvalidaError):
        leer_con_tope(bloques)


@pytest.mark.asyncio
async def test_should_no_escribir_when_calificacion_no_existe() -> None:
    servicio, almacen, _repo = _servicio(existe=False)
    with pytest.raises(CalificacionNoEncontradaError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", PDF, uuid4())
    assert almacen.guardados == {}


@pytest.mark.asyncio
async def test_should_responder_503_when_no_hay_raiz() -> None:
    servicio, almacen, _repo = _servicio(raiz=False)
    with pytest.raises(AlmacenamientoNoConfiguradoError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", PDF, uuid4())
    assert almacen.guardados == {}


@pytest.mark.asyncio
async def test_should_borrar_archivo_when_persistir_falla() -> None:
    servicio, almacen, _repo = _servicio(falla_guardar=True)
    with pytest.raises(RuntimeError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", PDF, uuid4())
    assert almacen.guardados == {}


def test_should_contener_la_ruta_en_la_raiz(tmp_path: Path) -> None:
    from src.infrastructure.almacenamiento.almacen_local import AlmacenLocal

    almacen = AlmacenLocal(tmp_path)
    almacen.guardar("evidencias/a/acta.pdf", PDF)
    assert (tmp_path / "evidencias" / "a" / "acta.pdf").read_bytes() == PDF
    with pytest.raises(ValueError):
        almacen.guardar("../fuera.pdf", PDF)
