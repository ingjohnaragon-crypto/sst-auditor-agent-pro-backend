"""Integración del flujo feliz de matriz GTC 45."""

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token


async def _crear_empresa(cliente: AsyncClient, headers: dict[str, str]) -> str:
    resp = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Matriz SA",
            "nit": "900333444-5",
            "actividad_economica": "Manufactura",
            "nivel_riesgo_arl": "III",
            "numero_trabajadores": 40,
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def test_should_completar_flujo_matriz_when_datos_validos(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    empresa_id = await _crear_empresa(cliente_async, headers)

    proceso = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers,
        json={"nombre": "Soldadura", "es_rutinaria": True, "zona_lugar": "Taller"},
    )
    assert proceso.status_code == 201, proceso.text
    proceso_id = proceso.json()["id"]

    peligro = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso_id}/peligros",
        headers=headers,
        json={
            "clasificacion": "FISICO",
            "descripcion": "Ruido continuo",
            "efectos_posibles": "Hipoacusia",
        },
    )
    assert peligro.status_code == 201, peligro.text
    peligro_id = peligro.json()["id"]

    evaluacion = await cliente_async.put(
        f"/api/v1/peligros/{peligro_id}/evaluacion",
        headers=headers,
        json={
            "nivel_deficiencia": 10,
            "nivel_exposicion": 4,
            "nivel_consecuencia": 100,
        },
    )
    assert evaluacion.status_code == 201, evaluacion.text
    body = evaluacion.json()
    assert body["nivel_probabilidad"] == 40
    assert body["nivel_riesgo"] == 4000
    assert body["interpretacion_nr"] == "I"
    assert body["aceptabilidad"] == "NO_ACEPTABLE"
    evaluacion_id = body["id"]

    # Upsert recalcula
    recal = await cliente_async.put(
        f"/api/v1/peligros/{peligro_id}/evaluacion",
        headers=headers,
        json={
            "nivel_deficiencia": 0,
            "nivel_exposicion": 4,
            "nivel_consecuencia": 100,
        },
    )
    assert recal.status_code == 200
    assert recal.json()["nivel_riesgo"] == 0
    assert recal.json()["interpretacion_nr"] == "IV"

    control = await cliente_async.post(
        f"/api/v1/evaluaciones-riesgo/{evaluacion_id}/controles",
        headers=headers,
        json={"tipo": "INGENIERIA", "descripcion": "Encerramiento"},
    )
    assert control.status_code == 201, control.text

    matriz = await cliente_async.get(
        f"/api/v1/empresas/{empresa_id}/matriz-riesgos",
        headers=headers,
    )
    assert matriz.status_code == 200, matriz.text
    data = matriz.json()
    assert data["empresa_id"] == empresa_id
    assert len(data["procesos"]) == 1
    assert data["procesos"][0]["proceso"]["nombre"] == "Soldadura"
    assert len(data["procesos"][0]["peligros"]) == 1
    assert data["procesos"][0]["peligros"][0]["evaluacion"]["nivel_riesgo"] == 0
    assert len(data["procesos"][0]["peligros"][0]["controles"]) == 1

    borrado = await cliente_async.delete(
        f"/api/v1/procesos-actividades/{proceso_id}",
        headers=headers,
    )
    assert borrado.status_code == 204
    matriz_vacia = await cliente_async.get(
        f"/api/v1/empresas/{empresa_id}/matriz-riesgos",
        headers=headers,
    )
    assert matriz_vacia.json()["procesos"] == []


async def test_should_rechazar_escritura_when_rol_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    admin = await obtener_token(cliente_async, usuarios_semilla)
    empresa_id = await _crear_empresa(cliente_async, bearer(admin))

    consulta = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    resp = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=bearer(consulta),
        json={"nombre": "X", "es_rutinaria": False},
    )
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "ACCESO_DENEGADO"


async def test_should_devolver_422_when_nd_invalido(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    empresa_id = await _crear_empresa(cliente_async, headers)
    proceso = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers,
        json={"nombre": "P", "es_rutinaria": True},
    )
    peligro = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso.json()['id']}/peligros",
        headers=headers,
        json={"clasificacion": "QUIMICO", "descripcion": "Solvente"},
    )
    resp = await cliente_async.put(
        f"/api/v1/peligros/{peligro.json()['id']}/evaluacion",
        headers=headers,
        json={
            "nivel_deficiencia": 5,
            "nivel_exposicion": 2,
            "nivel_consecuencia": 10,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["codigo"] == "VALOR_GTC_INVALIDO"


async def test_should_devolver_422_when_body_incluye_derivados(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    resp = await cliente_async.put(
        f"/api/v1/peligros/{uuid4()}/evaluacion",
        headers=headers,
        json={
            "nivel_deficiencia": 2,
            "nivel_exposicion": 2,
            "nivel_consecuencia": 10,
            "nivel_riesgo": 999,
        },
    )
    assert resp.status_code == 422


async def test_should_devolver_401_when_sin_token(
    cliente_async: AsyncClient,
) -> None:
    resp = await cliente_async.get(
        f"/api/v1/empresas/{uuid4()}/matriz-riesgos",
    )
    assert resp.status_code == 401
