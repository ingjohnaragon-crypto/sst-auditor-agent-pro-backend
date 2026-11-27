"""Pruebas de dominio del documento de empresa PHVA."""

from uuid import uuid4

import pytest
from src.domain.exceptions.documento_empresa import (
    DocumentoEstadoInvalidoError,
    DocumentoInvalidoError,
)
from src.domain.models.documento_empresa import (
    DocumentoEmpresa,
    EstadoDocumentoEmpresa,
    construir_clave_documento,
)


def test_should_crear_pendiente_sin_clave() -> None:
    documento = DocumentoEmpresa.pendiente(empresa_id=uuid4(), tipo_id=uuid4())
    assert documento.estado == EstadoDocumentoEmpresa.PENDIENTE
    assert documento.clave_objeto is None
    assert documento.id is None


def test_should_crear_cargado_y_construir_clave() -> None:
    empresa_id = uuid4()
    tipo_id = uuid4()
    clave = construir_clave_documento(empresa_id, "POLITICA_SST", ".pdf")
    documento = DocumentoEmpresa.crear_cargado(
        empresa_id=empresa_id,
        tipo_id=tipo_id,
        usuario_id=uuid4(),
        nombre_original="politica.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=120,
        clave_objeto=clave,
    )
    assert documento.estado == EstadoDocumentoEmpresa.CARGADO
    assert clave.startswith(f"documentos/{empresa_id}/POLITICA_SST/")
    assert clave.endswith(".pdf")


def test_should_marcar_revisado_solo_desde_cargado() -> None:
    empresa_id = uuid4()
    clave = construir_clave_documento(empresa_id, "PLAN_MEJORA", ".pdf")
    documento = DocumentoEmpresa.crear_cargado(
        empresa_id=empresa_id,
        tipo_id=uuid4(),
        usuario_id=uuid4(),
        nombre_original="plan.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=10,
        clave_objeto=clave,
    )
    documento.marcar_revisado()
    assert documento.estado == EstadoDocumentoEmpresa.REVISADO

    pendiente = DocumentoEmpresa.pendiente(empresa_id=empresa_id, tipo_id=uuid4())
    with pytest.raises(DocumentoEstadoInvalidoError):
        pendiente.marcar_revisado()


def test_should_devolver_clave_anterior_when_aplicar_carga() -> None:
    empresa_id = uuid4()
    clave_vieja = construir_clave_documento(empresa_id, "FURAT", ".pdf")
    documento = DocumentoEmpresa.crear_cargado(
        empresa_id=empresa_id,
        tipo_id=uuid4(),
        usuario_id=uuid4(),
        nombre_original="a.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=10,
        clave_objeto=clave_vieja,
    )
    clave_nueva = construir_clave_documento(empresa_id, "FURAT", ".pdf")
    anterior = documento.aplicar_carga(
        usuario_id=uuid4(),
        nombre_original="b.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=20,
        clave_objeto=clave_nueva,
    )
    assert anterior == clave_vieja
    assert documento.clave_objeto == clave_nueva
    assert documento.nombre_original == "b.pdf"


def test_should_rechazar_clave_invalida() -> None:
    with pytest.raises(DocumentoInvalidoError):
        construir_clave_documento(uuid4(), "../X", ".pdf")
    with pytest.raises(DocumentoInvalidoError):
        DocumentoEmpresa.crear_cargado(
            empresa_id=uuid4(),
            tipo_id=uuid4(),
            usuario_id=uuid4(),
            nombre_original="a.pdf",
            tipo_mime="application/pdf",
            tamano_bytes=1,
            clave_objeto="evidencias/x/y.pdf",
        )


def test_should_rechazar_extension_mime_tamano_y_comillas() -> None:
    empresa_id = uuid4()
    clave = construir_clave_documento(empresa_id, "POLITICA_SST", ".pdf")
    with pytest.raises(DocumentoInvalidoError, match="extensión"):
        DocumentoEmpresa.crear_cargado(
            empresa_id=empresa_id,
            tipo_id=uuid4(),
            usuario_id=uuid4(),
            nombre_original="acta.png",
            tipo_mime="application/pdf",
            tamano_bytes=10,
            clave_objeto=clave,
        )
    with pytest.raises(DocumentoInvalidoError, match="10 MiB"):
        DocumentoEmpresa.crear_cargado(
            empresa_id=empresa_id,
            tipo_id=uuid4(),
            usuario_id=uuid4(),
            nombre_original="acta.pdf",
            tipo_mime="application/pdf",
            tamano_bytes=10 * 1024 * 1024 + 1,
            clave_objeto=clave,
        )
    with pytest.raises(DocumentoInvalidoError, match="comillas"):
        DocumentoEmpresa.crear_cargado(
            empresa_id=empresa_id,
            tipo_id=uuid4(),
            usuario_id=uuid4(),
            nombre_original='evil".pdf',
            tipo_mime="application/pdf",
            tamano_bytes=10,
            clave_objeto=clave,
        )
