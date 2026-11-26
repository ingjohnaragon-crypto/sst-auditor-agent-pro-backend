"""Integración HTTP del repositorio documental de empresa."""

from uuid import UUID, uuid4

from fastapi import Depends
from httpx import AsyncClient
from src.application.services.servicio_archivos_documentales import (
    ServicioArchivosDocumentales,
)
from src.domain.repositories.repositorio_archivo_documental import (
    RepositorioArchivoDocumental,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.main import app
from src.presentation.dependencies.archivo_documental import (
    obtener_repositorio_archivo_documental,
    obtener_servicio_archivos_documentales,
)
from src.presentation.dependencies.autenticacion import obtener_repositorio_usuario

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

PDF = b"%PDF-1.4 documental"
PNG_INVALIDO_COMO_PDF = b"\x89PNG\r\n\x1a\n"


def _override_servicio(
    almacen: AlmacenMemoria,
    *,
    r2_configurado: bool = True,
) -> None:
    def override(
        repositorio: RepositorioArchivoDocumental = Depends(obtener_repositorio_archivo_documental),
        repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    ) -> ServicioArchivosDocumentales:
        return ServicioArchivosDocumentales(
            repositorio=repositorio,
            almacen=almacen,
            repositorio_usuario=repositorio_usuario,
            r2_configurado=r2_configurado,
        )

    app.dependency_overrides[obtener_servicio_archivos_documentales] = override


async def _crear_empresa(cliente: AsyncClient, headers: dict[str, str]) -> UUID:
    respuesta = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Archivos SA",
            "nit": f"900{uuid4().int % 10_000_000:07d}-1",
            "actividad_economica": "Consultoría SST",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 8,
        },
    )
    assert respuesta.status_code == 201
    return UUID(respuesta.json()["id"])


async def test_should_cargar_listar_descargar_y_eliminar(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        empresa_id = await _crear_empresa(cliente_async, headers)

        alta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201
        cuerpo = alta.json()
        assert cuerpo["nombre_original"] == "acta.pdf"
        assert "clave_objeto" not in cuerpo
        assert len(almacen.objetos) == 1
        archivo_id = cuerpo["id"]

        listado = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
        )
        assert listado.status_code == 200
        assert len(listado.json()) == 1

        descarga = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/archivos/{archivo_id}",
            headers=headers,
        )
        assert descarga.status_code == 200
        assert descarga.content == PDF
        assert descarga.headers["content-type"].startswith("application/pdf")

        borrado = await cliente_async.delete(
            f"/api/v1/empresas/{empresa_id}/archivos/{archivo_id}",
            headers=headers,
        )
        assert borrado.status_code == 204
        assert almacen.objetos == {}
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)


async def test_should_responder_401_when_anonimo(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    _override_servicio(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        empresa_id = await _crear_empresa(cliente_async, bearer(token))
        respuesta = await cliente_async.get(f"/api/v1/empresas/{empresa_id}/archivos")
        assert respuesta.status_code == 401
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)


async def test_should_responder_403_when_consulta_carga_o_borra(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        token_admin = await obtener_token(cliente_async, usuarios_semilla)
        headers_admin = bearer(token_admin)
        empresa_id = await _crear_empresa(cliente_async, headers_admin)
        alta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers_admin,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201

        token_consulta = await obtener_token(
            cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
        )
        headers_consulta = bearer(token_consulta)

        carga = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers_consulta,
            files={"archivo": ("otro.pdf", PDF, "application/pdf")},
        )
        assert carga.status_code == 403

        borrado = await cliente_async.delete(
            f"/api/v1/empresas/{empresa_id}/archivos/{alta.json()['id']}",
            headers=headers_consulta,
        )
        assert borrado.status_code == 403

        listado = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers_consulta,
        )
        assert listado.status_code == 200

        descarga = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/archivos/{alta.json()['id']}",
            headers=headers_consulta,
        )
        assert descarga.status_code == 200
        assert descarga.content == PDF
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)


async def test_should_no_dejar_objeto_when_archivo_invalido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        empresa_id = await _crear_empresa(cliente_async, headers)
        respuesta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
            files={"archivo": ("acta.pdf", PNG_INVALIDO_COMO_PDF, "application/pdf")},
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["codigo"] == "ARCHIVO_INVALIDO"
        assert almacen.objetos == {}
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)


async def test_should_responder_503_when_r2_no_configurado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen, r2_configurado=False)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        empresa_id = await _crear_empresa(cliente_async, headers)
        respuesta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 503
        assert respuesta.json()["codigo"] == "ALMACENAMIENTO_NO_CONFIGURADO"
        assert almacen.objetos == {}
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)


async def test_should_responder_404_when_empresa_inexistente(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    _override_servicio(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        empresa_id = uuid4()

        listado = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
        )
        assert listado.status_code == 404
        assert listado.json()["codigo"] == "EMPRESA_NO_ENCONTRADA"

        carga = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/archivos",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert carga.status_code == 404
        assert carga.json()["codigo"] == "EMPRESA_NO_ENCONTRADA"
    finally:
        app.dependency_overrides.pop(obtener_servicio_archivos_documentales, None)
