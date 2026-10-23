"""Integración HTTP del borrador de acciones desde incumplimientos."""

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

_EMPRESA = {
    "razon_social": "Empresa Acciones SA",
    "nit": "901260000-1",
    "actividad_economica": "Consultoría SST",
    "nivel_riesgo_arl": "III",
    "numero_trabajadores": 25,
}


def _error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo


def _clave_numeral(numeral: str) -> tuple[tuple[int, int | str], ...]:
    clave: list[tuple[int, int | str]] = []
    for parte in numeral.split("."):
        if parte.isdigit():
            clave.append((0, int(parte)))
        else:
            clave.append((1, parte))
    return tuple(clave)


async def _plan_con_resultados(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
    *,
    nit: str,
    no_cumple: set[int],
    no_aplica: set[int],
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
        if indice in no_cumple:
            resultado = "NO_CUMPLE"
        elif indice in no_aplica:
            resultado = "NO_APLICA"
        else:
            resultado = "CUMPLE"
        calificacion = await cliente.put(
            f"/api/v1/autoevaluaciones/{auto_id}/calificaciones/{estandar_id}",
            headers=headers,
            json={"resultado": resultado},
        )
        assert calificacion.status_code == 200
    fin = await cliente.post(f"/api/v1/autoevaluaciones/{auto_id}/finalizar", headers=headers)
    assert fin.status_code == 200
    assert fin.json()["requiere_plan_mejora"] is True
    creado = await cliente.post(
        f"/api/v1/autoevaluaciones/{auto_id}/plan-mejora",
        headers=headers,
        json={},
    )
    assert creado.status_code == 201
    return str(creado.json()["id"])


async def test_should_generar_borrador_sin_duplicar(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    plan_id = await _plan_con_resultados(
        cliente_async,
        headers,
        catalogo_semilla,
        nit="901260001-1",
        no_cumple={0, 2},
        no_aplica={1},
    )
    catalogo = await cliente_async.get("/api/v1/estandares-minimos", headers=headers)
    assert catalogo.status_code == 200
    por_id = {item["id"]: item for item in catalogo.json()}
    esperado_ids = {
        str(catalogo_semilla.estandar_ids[0]),
        str(catalogo_semilla.estandar_ids[2]),
    }

    primero = await cliente_async.post(
        f"/api/v1/planes-mejora/{plan_id}/acciones/borrador",
        headers=headers,
    )
    assert primero.status_code == 200
    cuerpo = primero.json()
    assert {item["estandar_id"] for item in cuerpo} == esperado_ids
    assert [item["numeral"] for item in cuerpo] == sorted(
        (por_id[item["estandar_id"]]["numeral"] for item in cuerpo),
        key=_clave_numeral,
    )
    for item in cuerpo:
        estandar = por_id[item["estandar_id"]]
        assert item["ciclo_phva"] == estandar["ciclo_phva"]
        assert item["descripcion"] == estandar["descripcion"]
        assert item["responsable_sugerido"] is None
        assert item["plan_id"] == plan_id

    segundo = await cliente_async.post(
        f"/api/v1/planes-mejora/{plan_id}/acciones/borrador",
        headers=headers,
    )
    assert segundo.status_code == 200
    assert [item["id"] for item in segundo.json()] == [item["id"] for item in cuerpo]

    leido = await cliente_async.get(f"/api/v1/planes-mejora/{plan_id}/acciones", headers=headers)
    assert leido.status_code == 200
    assert [item["id"] for item in leido.json()] == [item["id"] for item in cuerpo]


async def test_should_leer_y_no_generar_when_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token_admin = await obtener_token(cliente_async, usuarios_semilla)
    headers_admin = bearer(token_admin)
    plan_id = await _plan_con_resultados(
        cliente_async,
        headers_admin,
        catalogo_semilla,
        nit="901260002-1",
        no_cumple={0},
        no_aplica=set(),
    )
    token_consulta = await obtener_token(
        cliente_async,
        usuarios_semilla,
        correo=usuarios_semilla.correo_consulta,
    )
    headers_consulta = bearer(token_consulta)

    leido = await cliente_async.get(
        f"/api/v1/planes-mejora/{plan_id}/acciones",
        headers=headers_consulta,
    )
    assert leido.status_code == 200
    assert leido.json() == []

    denegado = await cliente_async.post(
        f"/api/v1/planes-mejora/{plan_id}/acciones/borrador",
        headers=headers_consulta,
    )
    assert denegado.status_code == 403
    _error(denegado.json(), "ACCESO_DENEGADO")


async def test_should_responder_401_when_no_hay_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.post(
        f"/api/v1/planes-mejora/{uuid4()}/acciones/borrador",
    )
    assert respuesta.status_code == 401


async def test_should_responder_404_when_el_plan_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    respuesta = await cliente_async.post(
        f"/api/v1/planes-mejora/{uuid4()}/acciones/borrador",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    _error(respuesta.json(), "PLAN_MEJORA_NO_ENCONTRADO")


async def test_should_borrar_el_borrador_when_se_elimina_el_plan(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    plan_id = await _plan_con_resultados(
        cliente_async,
        headers,
        catalogo_semilla,
        nit="901260003-1",
        no_cumple={0},
        no_aplica=set(),
    )
    generado = await cliente_async.post(
        f"/api/v1/planes-mejora/{plan_id}/acciones/borrador",
        headers=headers,
    )
    assert generado.status_code == 200
    assert len(generado.json()) == 1

    borrado = await cliente_async.delete(f"/api/v1/planes-mejora/{plan_id}", headers=headers)
    assert borrado.status_code == 204

    ausente = await cliente_async.get(
        f"/api/v1/planes-mejora/{plan_id}/acciones",
        headers=headers,
    )
    assert ausente.status_code == 404
    _error(ausente.json(), "PLAN_MEJORA_NO_ENCONTRADO")
