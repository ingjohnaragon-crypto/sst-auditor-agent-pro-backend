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


async def test_should_responder_404_when_crear_con_empresa_inexistente(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=bearer(token),
        json={"empresa_id": str(uuid4()), "fecha": "2026-07-04"},
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "EMPRESA_NO_ENCONTRADA"


async def test_should_responder_404_when_calificar_estandar_inexistente(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    empresa = await cliente_async.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Est SA",
            "nit": "600222333-1",
            "actividad_economica": "C",
            "nivel_riesgo_arl": "I",
            "numero_trabajadores": 2,
        },
    )
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-07-05"},
    )
    respuesta = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/{uuid4()}",
        headers=headers,
        json={"resultado": "CUMPLE"},
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "ESTANDAR_NO_ENCONTRADO"


async def test_should_responder_403_when_consulta_escribe_autoevaluacion(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    admin = await obtener_token(cliente_async, usuarios_semilla)
    headers_admin = bearer(admin)
    empresa = await cliente_async.post(
        "/api/v1/empresas",
        headers=headers_admin,
        json={
            "razon_social": "RBAC Auto SA",
            "nit": "600444555-2",
            "actividad_economica": "D",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 5,
        },
    )
    empresa_id = empresa.json()["id"]
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers_admin,
        json={"empresa_id": empresa_id, "fecha": "2026-07-06"},
    )
    auto_id = auto.json()["id"]

    consulta = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    headers_consulta = bearer(consulta)

    crear = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers_consulta,
        json={"empresa_id": empresa_id, "fecha": "2026-07-07"},
    )
    assert crear.status_code == 403
    assert crear.json()["codigo"] == "ACCESO_DENEGADO"

    calificar = await cliente_async.put(
        f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{catalogo_semilla.estandar_ids[0]}",
        headers=headers_consulta,
        json={"resultado": "CUMPLE"},
    )
    assert calificar.status_code == 403
    assert calificar.json()["codigo"] == "ACCESO_DENEGADO"

    finalizar = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/finalizar",
        headers=headers_consulta,
    )
    assert finalizar.status_code == 403
    assert finalizar.json()["codigo"] == "ACCESO_DENEGADO"


async def test_should_responder_409_when_finalizar_ya_finalizada(
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
            "razon_social": "Fin Dup SA",
            "nit": "600666777-3",
            "actividad_economica": "E",
            "nivel_riesgo_arl": "III",
            "numero_trabajadores": 8,
        },
    )
    auto = await cliente_async.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-07-08"},
    )
    auto_id = auto.json()["id"]
    for estandar_id in catalogo_semilla.estandar_ids:
        cal = await cliente_async.put(
            f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{estandar_id}",
            headers=headers,
            json={"resultado": "CUMPLE"},
        )
        assert cal.status_code == 200

    primera = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/finalizar",
        headers=headers,
    )
    assert primera.status_code == 200

    segunda = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/finalizar",
        headers=headers,
    )
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "AUTOEVALUACION_FINALIZADA"
