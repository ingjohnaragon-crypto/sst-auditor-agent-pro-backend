"""Pruebas de la factoría y la clave R2 de `ArchivoDocumental`."""

from uuid import uuid4

import pytest
from src.domain.exceptions.archivo_documental import ArchivoInvalidoError
from src.domain.models.archivo_documental import (
    TAMANO_MAXIMO_BYTES,
    ArchivoDocumental,
    construir_clave_objeto,
    extension_para_mime,
)

HASH_VALIDO = "a" * 64


def _crear(
    *,
    nombre_original: str = "acta.pdf",
    tipo_mime: str = "application/pdf",
    tamano_bytes: int = 1024,
    hash_contenido: str = HASH_VALIDO,
    clave_objeto: str | None = None,
) -> ArchivoDocumental:
    empresa_id = uuid4()
    clave = f"evidencias/{empresa_id}/{uuid4()}.pdf" if clave_objeto is None else clave_objeto
    return ArchivoDocumental.crear(
        empresa_id=empresa_id,
        usuario_id=uuid4(),
        nombre_original=nombre_original,
        tipo_mime=tipo_mime,
        tamano_bytes=tamano_bytes,
        hash_contenido=hash_contenido,
        clave_objeto=clave,
    )


def test_should_crear_pdf_when_metadatos_validos() -> None:
    archivo = _crear()
    assert archivo.id is None
    assert archivo.tipo_mime == "application/pdf"
    assert archivo.hash == HASH_VALIDO
    assert archivo.clave_objeto.startswith("evidencias/")


def test_should_generar_dos_claves_distintas_con_mismo_nombre() -> None:
    empresa_id = uuid4()
    primera = construir_clave_objeto(empresa_id, ".pdf")
    segunda = construir_clave_objeto(empresa_id, extension_para_mime("application/pdf"))
    assert primera != segunda
    assert primera.startswith(f"evidencias/{empresa_id}/")
    assert segunda.endswith(".pdf")


@pytest.mark.parametrize(
    ("nombre", "mime"),
    [
        ("acta.png", "application/pdf"),
        ("virus.html", "text/html"),
        ("sin-extension", "application/pdf"),
    ],
)
def test_should_rechazar_when_mime_o_extension_no_coinciden(nombre: str, mime: str) -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(nombre_original=nombre, tipo_mime=mime)


def test_should_rechazar_when_tamano_es_cero() -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(tamano_bytes=0)


def test_should_rechazar_when_tamano_supera_10_mib() -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(tamano_bytes=TAMANO_MAXIMO_BYTES + 1)


def test_should_rechazar_when_hash_no_es_sha256_hex() -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(hash_contenido="abc")


@pytest.mark.parametrize(
    "clave",
    [
        "",
        "file:///tmp/acta.pdf",
        "https://evil.example/acta.pdf",
        "/absoluta/acta.pdf",
        "c:/windows/acta.pdf",
    ],
)
def test_should_rechazar_clave_objeto_invalida(clave: str) -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(clave_objeto=clave)


def test_should_aceptar_clave_r2_con_segmentos_punto_punto_en_nombre_uuid() -> None:
    """La clave es identificador de objeto; no se rechaza como path de disco con .. parts."""
    empresa_id = uuid4()
    clave = f"evidencias/{empresa_id}/{uuid4()}.pdf"
    archivo = _crear(clave_objeto=clave)
    assert archivo.clave_objeto == clave


def test_should_rechazar_nombre_con_ruta_o_vacio() -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(nombre_original="")
    with pytest.raises(ArchivoInvalidoError):
        _crear(nombre_original="carpeta/acta.pdf")


def test_should_rechazar_extension_de_clave_no_permitida() -> None:
    with pytest.raises(ArchivoInvalidoError):
        construir_clave_objeto(uuid4(), ".exe")


def test_should_normalizar_extension_jpeg_en_clave() -> None:
    clave = construir_clave_objeto(uuid4(), "jpeg")
    assert clave.endswith(".jpg")


def test_should_rechazar_mime_desconocido_en_extension_para_mime() -> None:
    with pytest.raises(ArchivoInvalidoError):
        extension_para_mime("text/plain")


def test_should_rechazar_clave_demasiado_larga() -> None:
    with pytest.raises(ArchivoInvalidoError):
        _crear(clave_objeto="x" * 501)
