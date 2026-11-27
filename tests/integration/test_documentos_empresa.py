"""Integración HTTP del catálogo documental PHVA."""

from uuid import UUID, uuid4

from fastapi import Depends
from httpx import AsyncClient
from scripts.sembrar_tipos_documento_sst import sembrar_tipos_documento_sst
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.application.services.servicio_documentos_empresa import ServicioDocumentosEmpresa
from src.domain.repositories.repositorio_documento_empresa import (
    RepositorioDocumentoEmpresa,
)
from src.domain.repositories.repositorio_tipo_documento_sst import (
    RepositorioTipoDocumentoSst,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.main import app
from src.presentation.dependencies.autenticacion import obtener_repositorio_usuario
from src.presentation.dependencies.documento_empresa import (
    obtener_repositorio_documento_empresa,
    obtener_repositorio_tipo_documento,
    obtener_servicio_documentos_empresa,
)

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

PDF = b"%PDF-1.4 phva"
PNG_INVALIDO_COMO_PDF = b"\x89PNG\r\n\x1a\n"


def _override_servicio(
    almacen: AlmacenMemoria,
    *,
    r2_configurado: bool = True,
) -> None:
    def override(
        repositorio_documento: RepositorioDocumentoEmpresa = Depends(
            obtener_repositorio_documento_empresa
        ),
        repositorio_tipo: RepositorioTipoDocumentoSst = Depends(obtener_repositorio_tipo_documento),
        repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    ) -> ServicioDocumentosEmpresa:
        return ServicioDocumentosEmpresa(
            repositorio_documento=repositorio_documento,
            repositorio_tipo=repositorio_tipo,
            almacen=almacen,
            repositorio_usuario=repositorio_usuario,
            r2_configurado=r2_configurado,
        )

    app.dependency_overrides[obtener_servicio_documentos_empresa] = override


async def _sembrar_tipos(cliente: AsyncClient) -> None:
    fabrica: async_sessionmaker[AsyncSession] = cliente.fabrica_sesion  # type: ignore[attr-defined]
    async with fabrica() as sesion:
        await sembrar_tipos_documento_sst(sesion)
        await sesion.commit()


async def _crear_empresa(cliente: AsyncClient, headers: dict[str, str]) -> UUID:
    respuesta = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa PHVA SA",
            "nit": f"800{uuid4().int % 10_000_000:07d}-1",
            "actividad_economica": "Consultoría SST",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 12,
        },
    )
    assert respuesta.status_code == 201
    return UUID(respuesta.json()["id"])


async def test_should_catalogo_cargar_descargar_revisar_y_reemplazar(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        await _sembrar_tipos(cliente_async)
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)

        catalogo = await cliente_async.get("/api/v1/catalogo-documentos", headers=headers)
        assert catalogo.status_code == 200
        tipos = catalogo.json()
        assert len(tipos) == 10
        assert "clave_objeto" not in tipos[0]
        tipo_id = tipos[0]["id"]
        assert isinstance(tipos[0].get("estandares_ids"), list)

        empresa_id = await _crear_empresa(cliente_async, headers)
        listado = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/documentos",
            headers=headers,
        )
        assert listado.status_code == 200
        assert len(listado.json()) == 10
        assert all(item["estado"] == "PENDIENTE" for item in listado.json())
        assert all("clave_objeto" not in item for item in listado.json())

        alta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers,
            files={"archivo": ("politica.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201
        assert alta.json()["estado"] == "CARGADO"
        assert "clave_objeto" not in alta.json()
        assert len(almacen.objetos) == 1
        clave_vieja = next(iter(almacen.objetos))

        descarga = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers,
        )
        assert descarga.status_code == 200
        assert descarga.content == PDF

        segunda = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers,
            files={"archivo": ("politica2.pdf", PDF + b"2", "application/pdf")},
        )
        assert segunda.status_code == 201
        assert len(almacen.objetos) == 1
        assert clave_vieja not in almacen.objetos

        patch_ok = await cliente_async.patch(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}",
            headers=headers,
            json={"estado": "REVISADO"},
        )
        assert patch_ok.status_code == 200
        assert patch_ok.json()["estado"] == "REVISADO"

        patch_duplicado = await cliente_async.patch(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}",
            headers=headers,
            json={"estado": "REVISADO"},
        )
        assert patch_duplicado.status_code == 409
        assert patch_duplicado.json()["codigo"] == "CONFLICTO_ESTADO_DOCUMENTO"
    finally:
        app.dependency_overrides.pop(obtener_servicio_documentos_empresa, None)


async def test_should_rechazar_invalidos_403_401_409_503(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        await _sembrar_tipos(cliente_async)
        token_admin = await obtener_token(cliente_async, usuarios_semilla)
        headers_admin = bearer(token_admin)
        catalogo = await cliente_async.get("/api/v1/catalogo-documentos", headers=headers_admin)
        tipo_id = catalogo.json()[0]["id"]
        empresa_id = await _crear_empresa(cliente_async, headers_admin)

        invalido = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers_admin,
            files={"archivo": ("x.pdf", PNG_INVALIDO_COMO_PDF, "application/pdf")},
        )
        assert invalido.status_code == 422
        assert invalido.json()["codigo"] == "DOCUMENTO_INVALIDO"
        assert almacen.objetos == {}

        conflict = await cliente_async.patch(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}",
            headers=headers_admin,
            json={"estado": "REVISADO"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["codigo"] == "CONFLICTO_ESTADO_DOCUMENTO"

        await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers_admin,
            files={"archivo": ("ok.pdf", PDF, "application/pdf")},
        )

        token_consulta = await obtener_token(
            cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
        )
        headers_consulta = bearer(token_consulta)
        carga_consulta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers_consulta,
            files={"archivo": ("no.pdf", PDF, "application/pdf")},
        )
        assert carga_consulta.status_code == 403

        get_consulta = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers_consulta,
        )
        assert get_consulta.status_code == 200

        anon = await cliente_async.get(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo"
        )
        assert anon.status_code == 401
    finally:
        app.dependency_overrides.pop(obtener_servicio_documentos_empresa, None)

    _override_servicio(AlmacenMemoria(), r2_configurado=False)
    try:
        await _sembrar_tipos(cliente_async)
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        catalogo = await cliente_async.get("/api/v1/catalogo-documentos", headers=headers)
        tipo_id = catalogo.json()[0]["id"]
        empresa_id = await _crear_empresa(cliente_async, headers)
        sin_r2 = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo",
            headers=headers,
            files={"archivo": ("ok.pdf", PDF, "application/pdf")},
        )
        assert sin_r2.status_code == 503
        assert sin_r2.json()["codigo"] == "ALMACENAMIENTO_NO_CONFIGURADO"
    finally:
        app.dependency_overrides.pop(obtener_servicio_documentos_empresa, None)


async def test_should_cargar_tipo_sin_vinculo_0312(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    """Tipo sin estándar vinculado sigue siendo cargable (SP-268)."""
    almacen = AlmacenMemoria()
    _override_servicio(almacen)
    try:
        await _sembrar_tipos(cliente_async)
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        catalogo = await cliente_async.get("/api/v1/catalogo-documentos", headers=headers)
        # En integración los estándares semilla son INT-*; los vínculos oficiales no existen
        tipo_sin = next(t for t in catalogo.json() if t["estandares_ids"] == [])
        empresa_id = await _crear_empresa(cliente_async, headers)
        alta = await cliente_async.post(
            f"/api/v1/empresas/{empresa_id}/documentos/{tipo_sin['id']}/archivo",
            headers=headers,
            files={"archivo": ("doc.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201
        assert len(almacen.objetos) == 1
    finally:
        app.dependency_overrides.pop(obtener_servicio_documentos_empresa, None)
