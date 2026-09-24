"""Pruebas de la factoría y la baja lógica de `Evidencia`."""

from uuid import uuid4

import pytest
from src.domain.exceptions.evidencia import EvidenciaInvalidaError, EvidenciaYaInactivaError
from src.domain.models.evidencia import TAMANO_MAXIMO_BYTES, Evidencia


def _crear(
    *,
    nombre_archivo: str = "acta.pdf",
    tipo_mime: str = "application/pdf",
    tamano_bytes: int = 1024,
    ruta_almacenamiento: str = "empresas/acta.pdf",
) -> Evidencia:
    return Evidencia.crear(
        calificacion_estandar_id=uuid4(),
        usuario_id=uuid4(),
        nombre_archivo=nombre_archivo,
        tipo_mime=tipo_mime,
        tamano_bytes=tamano_bytes,
        ruta_almacenamiento=ruta_almacenamiento,
    )


def test_should_crear_pdf_when_metadatos_validos() -> None:
    evidencia = _crear()
    assert evidencia.activo is True
    assert evidencia.tipo_mime == "application/pdf"
    assert evidencia.fecha_eliminacion is None


@pytest.mark.parametrize("nombre", ["foto.jpg", "foto.jpeg", "FOTO.JPEG"])
def test_should_aceptar_jpeg_when_extension_coincide(nombre: str) -> None:
    evidencia = _crear(nombre_archivo=nombre, tipo_mime="image/jpeg")
    assert evidencia.tipo_mime == "image/jpeg"


def test_should_aceptar_png_when_extension_coincide() -> None:
    evidencia = _crear(nombre_archivo="plano.png", tipo_mime="image/png")
    assert evidencia.nombre_archivo == "plano.png"


@pytest.mark.parametrize(
    ("nombre", "mime"),
    [
        ("acta.png", "application/pdf"),
        ("virus.html", "text/html"),
        ("virus.exe", "application/x-msdownload"),
        ("sin-extension", "application/pdf"),
    ],
)
def test_should_rechazar_when_mime_o_extension_no_coinciden(nombre: str, mime: str) -> None:
    with pytest.raises(EvidenciaInvalidaError):
        _crear(nombre_archivo=nombre, tipo_mime=mime)


def test_should_rechazar_when_tamano_es_cero() -> None:
    with pytest.raises(EvidenciaInvalidaError):
        _crear(tamano_bytes=0)


def test_should_aceptar_when_tamano_es_el_maximo() -> None:
    evidencia = _crear(tamano_bytes=TAMANO_MAXIMO_BYTES)
    assert evidencia.tamano_bytes == TAMANO_MAXIMO_BYTES


def test_should_rechazar_when_tamano_supera_10_mib() -> None:
    with pytest.raises(EvidenciaInvalidaError):
        _crear(tamano_bytes=TAMANO_MAXIMO_BYTES + 1)


@pytest.mark.parametrize(
    "ruta",
    [
        "../secreto.pdf",
        "carpeta/../../secreto.pdf",
        "https://evil.example/acta.pdf",
        "file:///tmp/acta.pdf",
        "/absoluta/acta.pdf",
        "",
    ],
)
def test_should_rechazar_when_ruta_no_es_relativa_segura(ruta: str) -> None:
    with pytest.raises(EvidenciaInvalidaError):
        _crear(ruta_almacenamiento=ruta)


def test_should_marcar_inactiva_when_dar_de_baja() -> None:
    evidencia = _crear()
    evidencia.dar_de_baja()
    assert evidencia.activo is False
    assert evidencia.fecha_eliminacion is not None
    with pytest.raises(EvidenciaYaInactivaError):
        evidencia.dar_de_baja()
