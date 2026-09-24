"""Integración HTTP del enlace temporal de descarga."""

from pathlib import Path
from uuid import uuid4

from httpx import AsyncClient
from src.main import app
from src.presentation.dependencies.evidencia import obtener_raiz_almacenamiento

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

METADATOS = {
    "nombre_archivo": "acta.pdf",
    "tipo_mime": "application/pdf",
    "tamano_bytes": 2048,
    "ruta_almacenamiento": "empresas/acta.pdf",
}


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
            "nit": "900555666-7",
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


async def test_should_responder_403_when_consulta_pide_enlace(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
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


async def test_should_responder_404_when_evidencia_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.post(
        f"/api/v1/evidencias/{uuid4()}/enlace-descarga",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "EVIDENCIA_NO_ENCONTRADA"


async def test_should_rechazar_bearer_de_sesion_como_descarga(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(f"/api/v1/descargas/evidencias?token={token}")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"


async def test_should_servir_archivo_when_esta_en_la_raiz(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
    tmp_path: Path,
) -> None:
    destino = tmp_path / "empresas"
    destino.mkdir()
    (destino / "acta.pdf").write_bytes(b"%PDF-1.4")
    app.dependency_overrides[obtener_raiz_almacenamiento] = lambda: tmp_path
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
        assert canje.content.startswith(b"%PDF")
        assert "acta.pdf" in canje.headers.get("content-disposition", "")
    finally:
        app.dependency_overrides.pop(obtener_raiz_almacenamiento, None)
