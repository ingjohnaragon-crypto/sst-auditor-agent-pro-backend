"""Integración HTTP de la carga multipart de evidencias."""

from pathlib import Path
from uuid import uuid4

from httpx import AsyncClient
from src.main import app
from src.presentation.dependencies.evidencia import obtener_raiz_almacenamiento

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

PDF = b"%PDF-1.4 evidencia"


async def _calificacion_id(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
) -> str:
    empresa = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Carga SA",
            "nit": "900777888-9",
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
    return str(cal.json()["id"])


async def test_should_subir_y_descargar_el_mismo_archivo(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
    tmp_path: Path,
) -> None:
    app.dependency_overrides[obtener_raiz_almacenamiento] = lambda: tmp_path
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        calificacion_id = await _calificacion_id(cliente_async, headers, catalogo_semilla)
        alta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201
        assert alta.json()["tamano_bytes"] == len(PDF)
        assert (tmp_path / alta.json()["ruta_almacenamiento"]).read_bytes() == PDF

        enlace = await cliente_async.post(
            f"/api/v1/evidencias/{alta.json()['id']}/enlace-descarga",
            headers=headers,
        )
        assert enlace.status_code == 200
        canje = await cliente_async.get(enlace.json()["url"])
        assert canje.status_code == 200
        assert canje.content == PDF
    finally:
        app.dependency_overrides.pop(obtener_raiz_almacenamiento, None)


async def test_should_responder_403_when_consulta_sube(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
    tmp_path: Path,
) -> None:
    app.dependency_overrides[obtener_raiz_almacenamiento] = lambda: tmp_path
    try:
        token_admin = await obtener_token(cliente_async, usuarios_semilla)
        calificacion_id = await _calificacion_id(
            cliente_async, bearer(token_admin), catalogo_semilla
        )
        token_consulta = await obtener_token(
            cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
        )
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=bearer(token_consulta),
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"
    finally:
        app.dependency_overrides.pop(obtener_raiz_almacenamiento, None)


async def test_should_responder_404_when_calificacion_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    tmp_path: Path,
) -> None:
    app.dependency_overrides[obtener_raiz_almacenamiento] = lambda: tmp_path
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{uuid4()}/archivo",
            headers=bearer(token),
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 404
        assert respuesta.json()["codigo"] == "CALIFICACION_NO_ENCONTRADA"
    finally:
        app.dependency_overrides.pop(obtener_raiz_almacenamiento, None)


async def test_should_responder_422_y_no_dejar_archivo(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
    tmp_path: Path,
) -> None:
    app.dependency_overrides[obtener_raiz_almacenamiento] = lambda: tmp_path
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        calificacion_id = await _calificacion_id(cliente_async, headers, catalogo_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=headers,
            files={"archivo": ("acta.pdf", b"\x89PNG\r\n\x1a\n", "application/pdf")},
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["codigo"] == "EVIDENCIA_INVALIDA"
        assert list(tmp_path.rglob("*")) == []
    finally:
        app.dependency_overrides.pop(obtener_raiz_almacenamiento, None)


async def test_should_responder_503_when_no_hay_raiz(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    calificacion_id = await _calificacion_id(cliente_async, headers, catalogo_semilla)
    respuesta = await cliente_async.post(
        f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
        headers=headers,
        files={"archivo": ("acta.pdf", PDF, "application/pdf")},
    )
    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "ALMACENAMIENTO_NO_CONFIGURADO"
