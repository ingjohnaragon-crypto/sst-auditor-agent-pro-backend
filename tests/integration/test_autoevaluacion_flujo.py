"""Integración del flujo feliz de autoevaluación Res. 0312."""

from decimal import Decimal

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token


async def test_should_completar_flujo_autoevaluacion_when_datos_validos(
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
            "razon_social": "Empresa Flujo SA",
            "nit": "900111222-3",
            "actividad_economica": "Consultoría SST",
            "nivel_riesgo_arl": "III",
            "numero_trabajadores": 25,
        },
    )
    assert empresa.status_code == 201
    empresa_id = empresa.json()["id"]

    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa_id, "fecha": "2026-07-01"},
    )
    assert auto.status_code == 201
    auto_id = auto.json()["id"]
    assert auto.json()["puntaje_total"] is None

    for estandar_id in catalogo_semilla.estandar_ids:
        cal = await cliente_async.put(
            f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{estandar_id}",
            headers=headers,
            json={"resultado": "CUMPLE"},
        )
        assert cal.status_code == 200
        assert Decimal(str(cal.json()["puntaje"])) > 0

    # Upsert: recalificar no duplica
    recal = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{catalogo_semilla.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "CUMPLE", "observaciones": "ok"},
    )
    assert recal.status_code == 200

    fin = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/finalizar",
        headers=headers,
    )
    assert fin.status_code == 200
    body = fin.json()
    assert Decimal(str(body["puntaje_total"])) == Decimal("85.00")
    assert body["requiere_plan_mejora"] is False
    assert len(body["calificaciones"]) == 3

    historico = await cliente_async.get(
        f"/api/v1/autoevaluaciones?empresa_id={empresa_id}",
        headers=headers,
    )
    assert historico.status_code == 200
    assert len(historico.json()) == 1
    assert historico.json()[0]["calificaciones"] == []

    detalle = await cliente_async.get(f"/api/v1/autoevaluaciones/{auto_id}", headers=headers)
    assert detalle.status_code == 200
    assert len(detalle.json()["calificaciones"]) == 3

    # Tras finalizar, recalificar → 409
    bloqueado = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{catalogo_semilla.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "NO_CUMPLE"},
    )
    assert bloqueado.status_code == 409
    assert bloqueado.json()["codigo"] == "AUTOEVALUACION_FINALIZADA"
