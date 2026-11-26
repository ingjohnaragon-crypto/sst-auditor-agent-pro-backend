"""Pruebas unitarias de `ServicioArchivosDocumentales`."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.services.servicio_archivos_documentales import (
    ServicioArchivosDocumentales,
)
from src.domain.exceptions.archivo_documental import (
    ArchivoInvalidoError,
    ArchivoNoEncontradoError,
    ArchivoObjetoNoDisponibleError,
)
from src.domain.exceptions.autoevaluacion import EmpresaNoEncontradaError
from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.domain.models.archivo_documental import ArchivoDocumental
from src.domain.models.evidencia import TAMANO_MAXIMO_BYTES
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria

PDF = b"%PDF-1.4 contenido"
PDF_DEMASIADO_GRANDE = b"%PDF-1.4 " + (b"a" * TAMANO_MAXIMO_BYTES)


def _usuario(usuario_id=None) -> Usuario:
    return Usuario(
        id=usuario_id or uuid4(),
        nombre_completo="Ana Escritora",
        correo="ana@empresa.com",
        hash_contrasena="hash",
        rol=RolUsuario.AUDITOR_SST,
    )


def _servicio(
    *,
    r2: bool = True,
    existe_empresa: bool = True,
    almacen: AlmacenMemoria | None = None,
) -> tuple[ServicioArchivosDocumentales, AlmacenMemoria, AsyncMock]:
    repo = AsyncMock()
    repo.existe_empresa.return_value = existe_empresa
    repo_usuario = AsyncMock()
    repo_usuario.buscar_por_id.return_value = _usuario()
    memoria = almacen or AlmacenMemoria()

    async def _guardar(archivo: ArchivoDocumental) -> ArchivoDocumental:
        archivo.id = uuid4()
        return archivo

    repo.guardar.side_effect = _guardar
    servicio = ServicioArchivosDocumentales(
        repositorio=repo,
        almacen=memoria,
        repositorio_usuario=repo_usuario,
        r2_configurado=r2,
    )
    return servicio, memoria, repo


@pytest.mark.asyncio
async def test_should_cargar_when_pdf_valido() -> None:
    servicio, memoria, repo = _servicio()
    empresa_id = uuid4()
    usuario_id = uuid4()

    respuesta = await servicio.cargar(empresa_id, "acta.pdf", "application/pdf", PDF, usuario_id)

    assert respuesta.nombre_original == "acta.pdf"
    assert respuesta.tamano_bytes == len(PDF)
    assert "clave_objeto" not in respuesta.model_dump()
    assert len(memoria.objetos) == 1
    repo.guardar.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_no_guardar_en_almacen_when_magic_invalido() -> None:
    servicio, memoria, repo = _servicio()

    with pytest.raises(ArchivoInvalidoError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", b"no-es-pdf", uuid4())

    assert memoria.objetos == {}
    repo.guardar.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_rechazar_when_supera_tope_de_tamano() -> None:
    servicio, memoria, repo = _servicio()

    with pytest.raises(ArchivoInvalidoError):
        await servicio.cargar(
            uuid4(),
            "grande.pdf",
            "application/pdf",
            PDF_DEMASIADO_GRANDE,
            uuid4(),
        )

    assert memoria.objetos == {}
    repo.guardar.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_compensar_almacen_when_repo_falla() -> None:
    servicio, memoria, repo = _servicio()
    repo.guardar.side_effect = RuntimeError("db")

    with pytest.raises(RuntimeError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", PDF, uuid4())

    assert memoria.objetos == {}


@pytest.mark.asyncio
async def test_should_lanzar_503_when_r2_no_configurado() -> None:
    servicio, memoria, repo = _servicio(r2=False)

    with pytest.raises(AlmacenamientoNoConfiguradoError):
        await servicio.cargar(uuid4(), "acta.pdf", "application/pdf", PDF, uuid4())

    assert memoria.objetos == {}
    repo.guardar.assert_not_awaited()

    with pytest.raises(AlmacenamientoNoConfiguradoError):
        await servicio.eliminar(uuid4(), uuid4())
    repo.eliminar.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_lanzar_404_when_empresa_no_existe() -> None:
    servicio, _, _ = _servicio(existe_empresa=False)

    with pytest.raises(EmpresaNoEncontradaError):
        await servicio.listar(uuid4())


@pytest.mark.asyncio
async def test_should_descargar_y_eliminar() -> None:
    servicio, memoria, repo = _servicio()
    empresa_id = uuid4()
    usuario_id = uuid4()
    alta = await servicio.cargar(empresa_id, "acta.pdf", "application/pdf", PDF, usuario_id)
    clave = next(iter(memoria.objetos))
    archivo = ArchivoDocumental.crear(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        nombre_original="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=len(PDF),
        hash_contenido="a" * 64,
        clave_objeto=clave,
    )
    archivo.id = alta.id
    repo.buscar_por_id.return_value = archivo

    descarga = await servicio.descargar(empresa_id, alta.id)
    assert descarga.contenido == PDF

    await servicio.eliminar(empresa_id, alta.id)
    assert memoria.objetos == {}
    repo.eliminar.assert_awaited_once_with(alta.id)


@pytest.mark.asyncio
async def test_should_lanzar_objeto_no_disponible_when_falta_en_almacen() -> None:
    servicio, _, repo = _servicio()
    empresa_id = uuid4()
    archivo_id = uuid4()
    archivo = ArchivoDocumental.crear(
        empresa_id=empresa_id,
        usuario_id=uuid4(),
        nombre_original="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=10,
        hash_contenido="a" * 64,
        clave_objeto=f"evidencias/{empresa_id}/{uuid4()}.pdf",
    )
    archivo.id = archivo_id
    repo.buscar_por_id.return_value = archivo

    with pytest.raises(ArchivoObjetoNoDisponibleError):
        await servicio.descargar(empresa_id, archivo_id)


@pytest.mark.asyncio
async def test_should_lanzar_no_encontrado_when_archivo_de_otra_empresa() -> None:
    servicio, _, repo = _servicio()
    archivo = ArchivoDocumental.crear(
        empresa_id=uuid4(),
        usuario_id=uuid4(),
        nombre_original="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=10,
        hash_contenido="a" * 64,
        clave_objeto=f"evidencias/{uuid4()}/{uuid4()}.pdf",
    )
    archivo.id = uuid4()
    repo.buscar_por_id.return_value = archivo

    with pytest.raises(ArchivoNoEncontradoError):
        await servicio.descargar(uuid4(), archivo.id)
