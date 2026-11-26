"""Integración HTTP del enlace temporal de descarga."""

from uuid import uuid4

from fastapi import Depends
from httpx import AsyncClient
from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.config.settings import get_settings
from src.main import app
from src.presentation.dependencies.autenticacion import (
    obtener_repositorio_usuario,
    obtener_servicio_tokens,
)
from src.presentation.dependencies.evidencia import (
    obtener_repositorio_acceso_evidencia,
    obtener_repositorio_evidencia,
    obtener_servicio_descarga_evidencia,
)

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

CLAVE = "evidencias/emp-demo/acta.pdf"
METADATOS = {
    "nombre_archivo": "acta.pdf",
    "tipo_mime": "application/pdf",
    "tamano_bytes": 2048,
    "ruta_almacenamiento": CLAVE,
}
PDF = b"%PDF-1.4"


def _override_descarga(almacen: AlmacenMemoria) -> None:
    def override(
        repositorio_evidencia: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
        repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
        repositorio_acceso: RepositorioAccesoEvidencia = Depends(
            obtener_repositorio_acceso_evidencia
        ),
        servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
    ) -> ServicioDescargaEvidencia:
        settings = get_settings()
        return ServicioDescargaEvidencia(
            repositorio_evidencia=repositorio_evidencia,
            repositorio_usuario=repositorio_usuario,
            repositorio_acceso=repositorio_acceso,
            servicio_tokens=servicio_tokens,
            almacen=almacen,
            segundos_expiracion=settings.descarga_segundos_expiracion,
            prefijo_api=settings.api_prefix,
        )

    app.dependency_overrides[obtener_servicio_descarga_evidencia] = override


async def _evidencia_id(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
) -> str:
    empresa = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Descarga SA",
            "nit": f"900{uuid4().int % 10_000_000:07d}-7",
            "actividad_economica": "Consultoría SST",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 12,
        },
    )
    assert empresa.status_code == 201
    auto = await cliente.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-09-01"},
    )
    assert auto.status_code == 201
    cal = await cliente.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/{catalogo.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "CUMPLE"},
    )
    assert cal.status_code == 200
    alta = await cliente.post(
        f"/api/v1/calificaciones-estandar/{cal.json()['id']}/evidencias",
        headers=headers,
        json=METADATOS,
    )
    assert alta.status_code == 201
    return str(alta.json()["id"])


async def test_should_emitir_enlace_y_responder_archivo_no_disponible(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    _override_descarga(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        evidencia_id = await _evidencia_id(cliente_async, headers, catalogo_semilla)

        enlace = await cliente_async.post(
            f"/api/v1/evidencias/{evidencia_id}/enlace-descarga",
            headers=headers,
        )
        assert enlace.status_code == 200
        assert enlace.json()["expira_en_segundos"] <= 900
        url = enlace.json()["url"]

        canje = await cliente_async.get(url)
        assert canje.status_code == 404
        assert canje.json()["codigo"] == "ARCHIVO_NO_DISPONIBLE"
    finally:
        app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)


async def test_should_responder_403_when_consulta_pide_enlace(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    _override_descarga(AlmacenMemoria())
    try:
        token_admin = await obtener_token(cliente_async, usuarios_semilla)
        evidencia_id = await _evidencia_id(cliente_async, bearer(token_admin), catalogo_semilla)
        token_consulta = await obtener_token(
            cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
        )
        respuesta = await cliente_async.post(
            f"/api/v1/evidencias/{evidencia_id}/enlace-descarga",
            headers=bearer(token_consulta),
        )
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"
    finally:
        app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)


async def test_should_responder_404_when_evidencia_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    _override_descarga(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/evidencias/{uuid4()}/enlace-descarga",
            headers=bearer(token),
        )
        assert respuesta.status_code == 404
        assert respuesta.json()["codigo"] == "EVIDENCIA_NO_ENCONTRADA"
    finally:
        app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)


async def test_should_rechazar_bearer_de_sesion_como_descarga(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    _override_descarga(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        respuesta = await cliente_async.get(f"/api/v1/descargas/evidencias?token={token}")
        assert respuesta.status_code == 401
        assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"
    finally:
        app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)


async def test_should_servir_archivo_when_esta_en_almacen(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    almacen = AlmacenMemoria()
    almacen.guardar(CLAVE, PDF)
    _override_descarga(almacen)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        evidencia_id = await _evidencia_id(cliente_async, headers, catalogo_semilla)
        enlace = await cliente_async.post(
            f"/api/v1/evidencias/{evidencia_id}/enlace-descarga",
            headers=headers,
        )
        assert enlace.status_code == 200
        canje = await cliente_async.get(enlace.json()["url"])
        assert canje.status_code == 200
        assert canje.content == PDF
        assert "acta.pdf" in canje.headers.get("content-disposition", "")
    finally:
        app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)
