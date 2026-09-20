"""Integración del endpoint de cumplimiento PHVA (SP-149)."""

from decimal import Decimal

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token


async def test_should_devolver_cumplimiento_phva_when_autoevaluacion_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)

    empresa = await cliente_async.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa PHVA SA",
            "nit": "900333444-5",
            "actividad_economica": "Consultoría",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 8,
        },
    )
    assert empresa.status_code == 201
    empresa_id = empresa.json()["id"]

    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa_id, "fecha": "2026-07-10"},
    )
    assert auto.status_code == 201
    auto_id = auto.json()["id"]

    cal = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{catalogo_semilla.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "CUMPLE"},
    )
    assert cal.status_code == 200

    resumen = await cliente_async.get(
        f"/api/v1/autoevaluaciones/{auto_id}/cumplimiento-phva",
        headers=headers,
    )
    assert resumen.status_code == 200
    body = resumen.json()
    assert body["autoevaluacion_id"] == auto_id
    assert body["empresa_id"] == empresa_id
    assert body["perfil"] == "TABLA_7"
    assert body["finalizada"] is False
    assert body["umbral_plan_mejora"] == "85.00" or Decimal(
        str(body["umbral_plan_mejora"])
    ) == Decimal("85")
    assert len(body["fases"]) == 4
    ciclos = [fase["ciclo_phva"] for fase in body["fases"]]
    assert ciclos == ["PLANEAR", "HACER", "VERIFICAR", "ACTUAR"]


async def test_should_responder_404_when_cumplimiento_phva_inexistente(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.get(
        "/api/v1/autoevaluaciones/00000000-0000-0000-0000-000000000099/cumplimiento-phva",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "AUTOEVALUACION_NO_ENCONTRADA"


async def test_should_responder_401_when_cumplimiento_phva_sin_token(
    cliente_async: AsyncClient,
) -> None:
    respuesta = await cliente_async.get(
        "/api/v1/autoevaluaciones/00000000-0000-0000-0000-000000000099/cumplimiento-phva",
    )
    assert respuesta.status_code == 401


async def test_should_permitir_lectura_cumplimiento_phva_a_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token_auditor = await obtener_token(cliente_async, usuarios_semilla)
    headers_auditor = bearer(token_auditor)
    empresa = await cliente_async.post(
        "/api/v1/empresas",
        headers=headers_auditor,
        json={
            "razon_social": "Empresa Consulta PHVA",
            "nit": "900555666-7",
            "actividad_economica": "Servicios",
            "nivel_riesgo_arl": "I",
            "numero_trabajadores": 3,
        },
    )
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers_auditor,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-07-11"},
    )
    token_consulta = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    resumen = await cliente_async.get(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/cumplimiento-phva",
        headers=bearer(token_consulta),
    )
    assert resumen.status_code == 200
    assert resumen.json()["perfil"] == "TABLA_7"
