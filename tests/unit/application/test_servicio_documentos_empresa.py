"""Pruebas unitarias del servicio de documentos PHVA."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.services.servicio_documentos_empresa import ServicioDocumentosEmpresa
from src.domain.exceptions.documento_empresa import (
    DocumentoEstadoInvalidoError,
    DocumentoInvalidoError,
)
from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.domain.models.documento_empresa import DocumentoEmpresa, EstadoDocumentoEmpresa
from src.domain.models.tipo_documento_sst import FaseDocumentoPhva, TipoDocumentoSst
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria

PDF = b"%PDF-1.4 servicio"


def _tipo(codigo: str = "POLITICA_SST") -> TipoDocumentoSst:
    return TipoDocumentoSst(
        id=uuid4(),
        codigo=codigo,
        nombre="Política",
        fase=FaseDocumentoPhva.PLANEAR,
        descripcion="desc",
        obligatorio=True,
    )


def _servicio(
    *,
    r2: bool = True,
    almacen: AlmacenMemoria | None = None,
) -> tuple[ServicioDocumentosEmpresa, AlmacenMemoria, AsyncMock, AsyncMock]:
    docs = AsyncMock()
    tipos = AsyncMock()
    usuarios = AsyncMock()
    usuarios.buscar_por_id.return_value = None
    memoria = almacen or AlmacenMemoria()
    servicio = ServicioDocumentosEmpresa(
        repositorio_documento=docs,
        repositorio_tipo=tipos,
        almacen=memoria,
        repositorio_usuario=usuarios,
        r2_configurado=r2,
    )
    return servicio, memoria, docs, tipos


@pytest.mark.asyncio
async def test_should_cargar_y_reemplazar_clave() -> None:
    servicio, memoria, docs, tipos = _servicio()
    tipo = _tipo()
    empresa_id = uuid4()
    docs.existe_empresa.return_value = True
    tipos.buscar_por_id.return_value = tipo
    docs.buscar_por_empresa_y_tipo.return_value = None

    async def guardar(documento: DocumentoEmpresa) -> DocumentoEmpresa:
        documento.id = documento.id or uuid4()
        return documento

    docs.guardar.side_effect = guardar

    primero = await servicio.cargar(
        empresa_id,
        tipo.id,
        "a.pdf",
        "application/pdf",
        PDF,
        uuid4(),  # type: ignore[arg-type]
    )
    assert primero.estado == EstadoDocumentoEmpresa.CARGADO.value
    assert len(memoria.objetos) == 1
    clave1 = next(iter(memoria.objetos))

    existente = DocumentoEmpresa.crear_cargado(
        empresa_id=empresa_id,
        tipo_id=tipo.id,  # type: ignore[arg-type]
        usuario_id=uuid4(),
        nombre_original="a.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=len(PDF),
        clave_objeto=clave1,
    )
    existente.id = uuid4()
    docs.buscar_por_empresa_y_tipo.return_value = existente

    await servicio.cargar(
        empresa_id,
        tipo.id,  # type: ignore[arg-type]
        "b.pdf",
        "application/pdf",
        PDF + b"x",
        uuid4(),
    )
    assert len(memoria.objetos) == 1
    assert clave1 not in memoria.objetos


@pytest.mark.asyncio
async def test_should_rechazar_sin_r2_y_contenido_invalido() -> None:
    servicio, _, docs, tipos = _servicio(r2=False)
    docs.existe_empresa.return_value = True
    with pytest.raises(AlmacenamientoNoConfiguradoError):
        await servicio.cargar(uuid4(), uuid4(), "a.pdf", "application/pdf", PDF, uuid4())

    servicio2, memoria, docs2, tipos2 = _servicio()
    docs2.existe_empresa.return_value = True
    tipos2.buscar_por_id.return_value = _tipo()
    with pytest.raises(DocumentoInvalidoError):
        await servicio2.cargar(
            uuid4(),
            uuid4(),
            "a.pdf",
            "application/pdf",
            b"\x89PNG\r\n\x1a\n",
            uuid4(),
        )
    assert memoria.objetos == {}


@pytest.mark.asyncio
async def test_should_marcar_revisado_solo_cargado() -> None:
    servicio, _, docs, tipos = _servicio()
    tipo = _tipo()
    empresa_id = uuid4()
    docs.existe_empresa.return_value = True
    tipos.buscar_por_id.return_value = tipo
    docs.buscar_por_empresa_y_tipo.return_value = DocumentoEmpresa.pendiente(
        empresa_id=empresa_id,
        tipo_id=tipo.id,  # type: ignore[arg-type]
    )
    with pytest.raises(DocumentoEstadoInvalidoError):
        await servicio.marcar_revisado(empresa_id, tipo.id)  # type: ignore[arg-type]
