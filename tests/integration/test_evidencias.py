"""Integración HTTP de metadatos de evidencias."""

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

METADATOS = {
    "nombre_archivo": "acta.pdf",
    "tipo_mime": "application/pdf",
    "tamano_bytes": 2048,
    "ruta_almacenamiento": "empresas/acta.pdf",
}


async def _calificacion_id(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
) -> str:
    empresa = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Evidencias SA",
            "nit": "900333444-5",
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
    assert cal.json()["id"] is not None
    return str(cal.json()["id"])


async def test_should_registrar_listar_y_dar_de_baja_when_auditor(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    calificacion_id = await _calificacion_id(cliente_async, headers, catalogo_semilla)
    ruta = f"/api/v1/calificaciones-estandar/{calificacion_id}/evidencias"

    alta = await cliente_async.post(ruta, headers=headers, json=METADATOS)
    assert alta.status_code == 201
    cuerpo = alta.json()
    assert cuerpo["nombre_archivo"] == "acta.pdf"
    assert cuerpo["activo"] is True
    assert cuerpo["usuario_id"]
    evidencia_id = cuerpo["id"]

    listado = await cliente_async.get(ruta, headers=headers)
    assert listado.status_code == 200
    assert len(listado.json()) == 1

    baja = await cliente_async.delete(f"/api/v1/evidencias/{evidencia_id}", headers=headers)
    assert baja.status_code == 204
    assert baja.content == b""

    vacio = await cliente_async.get(ruta, headers=headers)
    assert vacio.status_code == 200
    assert vacio.json() == []

    segunda = await cliente_async.delete(f"/api/v1/evidencias/{evidencia_id}", headers=headers)
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "EVIDENCIA_YA_INACTIVA"


async def test_should_responder_403_when_consulta_escribe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token_admin = await obtener_token(cliente_async, usuarios_semilla)
    calificacion_id = await _calificacion_id(cliente_async, bearer(token_admin), catalogo_semilla)
    token_consulta = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    respuesta = await cliente_async.post(
        f"/api/v1/calificaciones-estandar/{calificacion_id}/evidencias",
        headers=bearer(token_consulta),
        json=METADATOS,
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"


async def test_should_responder_404_when_calificacion_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(
        f"/api/v1/calificaciones-estandar/{uuid4()}/evidencias",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "CALIFICACION_NO_ENCONTRADA"


async def test_should_responder_422_when_mime_no_permitido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    calificacion_id = await _calificacion_id(cliente_async, headers, catalogo_semilla)
    invalido = {**METADATOS, "nombre_archivo": "virus.exe", "tipo_mime": "application/x-msdownload"}
    respuesta = await cliente_async.post(
        f"/api/v1/calificaciones-estandar/{calificacion_id}/evidencias",
        headers=headers,
        json=invalido,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "EVIDENCIA_INVALIDA"
