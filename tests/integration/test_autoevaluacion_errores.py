"""Matriz de errores HTTP de empresas/autoevaluación (401/403/404/409/422)."""

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token


async def test_should_responder_401_when_sin_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.get("/api/v1/empresas")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"


async def test_should_responder_403_when_consulta_intenta_escribir(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    respuesta = await cliente_async.post(
        "/api/v1/empresas",
        headers=bearer(token),
        json={
            "razon_social": "X",
            "nit": "1",
            "actividad_economica": "Y",
            "nivel_riesgo_arl": "I",
            "numero_trabajadores": 1,
        },
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"


async def test_should_responder_409_when_nit_duplicado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    payload = {
        "razon_social": "Dup SA",
        "nit": "800999888-1",
        "actividad_economica": "Servicios",
        "nivel_riesgo_arl": "II",
        "numero_trabajadores": 3,
    }
    creada = await cliente_async.post("/api/v1/empresas", headers=headers, json=payload)
    assert creada.status_code == 201
    dup = await cliente_async.post("/api/v1/empresas", headers=headers, json=payload)
    assert dup.status_code == 409
    assert dup.json()["codigo"] == "NIT_DUPLICADO"


async def test_should_responder_422_when_resultado_invalido_o_puntaje_enviado(
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
            "razon_social": "Val SA",
            "nit": "700111222-0",
            "actividad_economica": "A",
            "nivel_riesgo_arl": "I",
            "numero_trabajadores": 2,
        },
    )
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-07-02"},
    )
    estandar_id = catalogo_semilla.estandar_ids[0]
    invalid = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/{estandar_id}",
        headers=headers,
        json={"resultado": "TALVEZ"},
    )
    assert invalid.status_code == 422

    con_puntaje = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/{estandar_id}",
        headers=headers,
        json={"resultado": "CUMPLE", "puntaje": 99},
    )
    assert con_puntaje.status_code == 422


async def test_should_responder_404_when_recursos_inexistentes(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    fantasma = uuid4()

    empresa = await cliente_async.get(f"/api/v1/empresas/{fantasma}", headers=headers)
    assert empresa.status_code == 404
    assert empresa.json()["codigo"] == "EMPRESA_NO_ENCONTRADA"

    auto = await cliente_async.get(f"/api/v1/autoevaluaciones/{fantasma}", headers=headers)
    assert auto.status_code == 404
    assert auto.json()["codigo"] == "AUTOEVALUACION_NO_ENCONTRADA"


async def test_should_responder_409_when_finalizar_incompleta(
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
            "razon_social": "Inc SA",
            "nit": "600123123-9",
            "actividad_economica": "B",
            "nivel_riesgo_arl": "IV",
            "numero_trabajadores": 4,
        },
    )
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-07-03"},
    )
    await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/"
        f"{catalogo_semilla.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "CUMPLE"},
    )
    fin = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/finalizar",
        headers=headers,
    )
    assert fin.status_code == 409
    assert fin.json()["codigo"] == "AUTOEVALUACION_INCOMPLETA"


async def test_should_filtrar_estandares_por_ciclo_phva(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)

    todos = await cliente_async.get("/api/v1/estandares-minimos", headers=headers)
    assert todos.status_code == 200
    assert len(todos.json()) == 3

    planear = await cliente_async.get(
        "/api/v1/estandares-minimos?ciclo_phva=PLANEAR", headers=headers
    )
    assert planear.status_code == 200
    assert all(e["ciclo_phva"] == "PLANEAR" for e in planear.json())
    assert len(planear.json()) == 2

    invalido = await cliente_async.get(
        "/api/v1/estandares-minimos?ciclo_phva=OTRO", headers=headers
    )
    assert invalido.status_code == 422
