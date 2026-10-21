"""Integración HTTP del plan de mejora."""

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

_EMPRESA = {
    "razon_social": "Empresa Plan SA",
    "nit": "901258000-1",
    "actividad_economica": "Consultoría SST",
    "nivel_riesgo_arl": "III",
    "numero_trabajadores": 25,
}


def _error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo


async def _autoevaluacion_finalizada(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
    *,
    exige_plan: bool,
    nit: str,
) -> str:
    empresa = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={**_EMPRESA, "nit": nit},
    )
    assert empresa.status_code == 201
    auto = await cliente.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa.json()["id"], "fecha": "2026-03-01"},
    )
    assert auto.status_code == 201
    auto_id = str(auto.json()["id"])
    for indice, estandar_id in enumerate(catalogo.estandar_ids):
        resultado = "NO_CUMPLE" if exige_plan and indice == 0 else "CUMPLE"
        calificacion = await cliente.put(
            f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{estandar_id}",
            headers=headers,
            json={"resultado": resultado},
        )
        assert calificacion.status_code == 200
    fin = await cliente.post(f"/api/v1/autoevaluaciones/{auto_id}/finalizar", headers=headers)
    assert fin.status_code == 200
    assert fin.json()["requiere_plan_mejora"] is exige_plan
    return auto_id


async def test_should_abrir_y_leer_plan_when_escritor(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    auto_id = await _autoevaluacion_finalizada(
        cliente_async,
        headers,
        catalogo_semilla,
        exige_plan=True,
        nit="901258001-1",
    )

    creado = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
        json={
            "actividades": [
                {
                    "descripcion": "Designar responsable",
                    "responsable": "Coordinador SST",
                    "indicador": "Acta",
                    "meses": [12, 1],
                }
            ]
        },
    )
    assert creado.status_code == 201
    cuerpo = creado.json()
    assert cuerpo["autoevaluacion_id"] == auto_id
    assert cuerpo["actividades"][0]["meses"] == [1, 12]

    leido = await cliente_async.get(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
    )
    assert leido.status_code == 200
    assert leido.json()["id"] == cuerpo["id"]


async def test_should_rechazar_segundo_plan_when_ya_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    auto_id = await _autoevaluacion_finalizada(
        cliente_async,
        headers,
        catalogo_semilla,
        exige_plan=True,
        nit="901258002-1",
    )
    ruta = f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora"
    primero = await cliente_async.post(ruta, headers=headers, json={})
    assert primero.status_code == 201

    segundo = await cliente_async.post(ruta, headers=headers, json={})
    assert segundo.status_code == 409
    _error(segundo.json(), "PLAN_MEJORA_YA_EXISTE")


async def test_should_leer_y_no_escribir_when_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token_admin = await obtener_token(cliente_async, usuarios_semilla)
    headers_admin = bearer(token_admin)
    auto_id = await _autoevaluacion_finalizada(
        cliente_async,
        headers_admin,
        catalogo_semilla,
        exige_plan=True,
        nit="901258003-1",
    )
    creado = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers_admin,
        json={},
    )
    assert creado.status_code == 201

    token_consulta = await obtener_token(
        cliente_async,
        usuarios_semilla,
        correo=usuarios_semilla.correo_consulta,
    )
    headers_consulta = bearer(token_consulta)
    leido = await cliente_async.get(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers_consulta,
    )
    assert leido.status_code == 200

    denegado = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers_consulta,
        json={},
    )
    assert denegado.status_code == 403
    _error(denegado.json(), "ACCESO_DENEGADO")


async def test_should_responder_401_when_no_hay_token(
    cliente_async: AsyncClient,
) -> None:
    respuesta = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{'0' * 8}-0000-0000-0000-000000000001/plan-mejora",
        json={},
    )
    assert respuesta.status_code == 401


async def test_should_rechazar_plan_when_la_autoevaluacion_es_aceptable(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    auto_id = await _autoevaluacion_finalizada(
        cliente_async,
        headers,
        catalogo_semilla,
        exige_plan=False,
        nit="901258004-1",
    )

    respuesta = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
        json={},
    )
    assert respuesta.status_code == 409
    _error(respuesta.json(), "PLAN_MEJORA_NO_REQUERIDO")


async def test_should_editar_actividades_y_borrar_plan(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    auto_id = await _autoevaluacion_finalizada(
        cliente_async,
        headers,
        catalogo_semilla,
        exige_plan=True,
        nit="901258005-1",
    )
    creado = await cliente_async.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
        json={},
    )
    assert creado.status_code == 201
    plan_id = creado.json()["id"]

    detalle = await cliente_async.get(f"/api/v1/planes-mejora/{plan_id}", headers=headers)
    assert detalle.status_code == 200
    assert detalle.json()["actividades"] == []

    agregada = await cliente_async.post(
        f"/api/v1/planes-mejora/{plan_id}/actividades",
        headers=headers,
        json={
            "descripcion": "Capacitar",
            "responsable": "Jefe SST",
            "indicador": "Listado",
            "meses": [3],
        },
    )
    assert agregada.status_code == 201
    actividad_id = agregada.json()["actividades"][0]["id"]

    actualizada = await cliente_async.put(
        f"/api/v1/planes-mejora/{plan_id}/actividades/{actividad_id}",
        headers=headers,
        json={
            "descripcion": "Reentrenar",
            "responsable": "Jefe SST",
            "indicador": "Acta",
            "meses": [4],
        },
    )
    assert actualizada.status_code == 200
    assert actualizada.json()["actividades"][0]["id"] == actividad_id
    assert actualizada.json()["actividades"][0]["meses"] == [4]

    quitada = await cliente_async.delete(
        f"/api/v1/planes-mejora/{plan_id}/actividades/{actividad_id}",
        headers=headers,
    )
    assert quitada.status_code == 204

    borrado = await cliente_async.delete(f"/api/v1/planes-mejora/{plan_id}", headers=headers)
    assert borrado.status_code == 204

    ausente = await cliente_async.get(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
    )
    assert ausente.status_code == 404
    _error(ausente.json(), "PLAN_MEJORA_NO_ENCONTRADO")
