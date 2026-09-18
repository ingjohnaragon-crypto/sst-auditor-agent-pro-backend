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
    headers_admin = bearer(admin)
    empresa_id = await _crear_empresa(cliente_async, headers_admin)
    proceso = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers_admin,
        json={"nombre": "Base", "es_rutinaria": True},
    )
    assert proceso.status_code == 201, proceso.text
    proceso_id = proceso.json()["id"]
    peligro = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso_id}/peligros",
        headers=headers_admin,
        json={"clasificacion": "FISICO", "descripcion": "Ruido"},
    )
    assert peligro.status_code == 201, peligro.text
    peligro_id = peligro.json()["id"]

    consulta = await obtener_token(
        cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
    )
    headers_consulta = bearer(consulta)

    post_proceso = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers_consulta,
        json={"nombre": "X", "es_rutinaria": False},
    )
    assert post_proceso.status_code == 403
    assert post_proceso.json()["codigo"] == "ACCESO_DENEGADO"

    put_eval = await cliente_async.put(
        f"/api/v1/peligros/{peligro_id}/evaluacion",
        headers=headers_consulta,
        json={
            "nivel_deficiencia": 2,
            "nivel_exposicion": 2,
            "nivel_consecuencia": 10,
        },
    )
    assert put_eval.status_code == 403
    assert put_eval.json()["codigo"] == "ACCESO_DENEGADO"

    delete_proceso = await cliente_async.delete(
        f"/api/v1/procesos-actividades/{proceso_id}",
        headers=headers_consulta,
    )
    assert delete_proceso.status_code == 403
    assert delete_proceso.json()["codigo"] == "ACCESO_DENEGADO"

    post_peligro = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso_id}/peligros",
        headers=headers_consulta,
        json={"clasificacion": "BIOLOGICO", "descripcion": "X"},
    )
    assert post_peligro.status_code == 403
    assert post_peligro.json()["codigo"] == "ACCESO_DENEGADO"

    post_control = await cliente_async.post(
        f"/api/v1/evaluaciones-riesgo/{uuid4()}/controles",
        headers=headers_consulta,
        json={"tipo": "EPP", "descripcion": "Casco"},
    )
    assert post_control.status_code == 403
    assert post_control.json()["codigo"] == "ACCESO_DENEGADO"


async def test_should_devolver_404_when_recursos_inexistentes(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    fantasma = uuid4()

    matriz = await cliente_async.get(
        f"/api/v1/empresas/{fantasma}/matriz-riesgos",
        headers=headers,
    )
    assert matriz.status_code == 404
    assert matriz.json()["codigo"] == "EMPRESA_NO_ENCONTRADA"

    proceso = await cliente_async.get(
        f"/api/v1/procesos-actividades/{fantasma}",
        headers=headers,
    )
    assert proceso.status_code == 404
    assert proceso.json()["codigo"] == "PROCESO_NO_ENCONTRADO"

    peligro = await cliente_async.get(f"/api/v1/peligros/{fantasma}", headers=headers)
    assert peligro.status_code == 404
    assert peligro.json()["codigo"] == "PELIGRO_NO_ENCONTRADO"

    control = await cliente_async.patch(
        f"/api/v1/controles-riesgo/{fantasma}",
        headers=headers,
        json={"descripcion": "X"},
    )
    assert control.status_code == 404
    assert control.json()["codigo"] == "CONTROL_NO_ENCONTRADO"

    delete_control = await cliente_async.delete(
        f"/api/v1/controles-riesgo/{fantasma}",
        headers=headers,
    )
    assert delete_control.status_code == 404
    assert delete_control.json()["codigo"] == "CONTROL_NO_ENCONTRADO"

    patch_proceso = await cliente_async.patch(
        f"/api/v1/procesos-actividades/{fantasma}",
        headers=headers,
        json={"nombre": "Fantasma", "es_rutinaria": True},
    )
    assert patch_proceso.status_code == 404
    assert patch_proceso.json()["codigo"] == "PROCESO_NO_ENCONTRADO"

    post_peligro_fantasma = await cliente_async.post(
        f"/api/v1/procesos-actividades/{fantasma}/peligros",
        headers=headers,
        json={"clasificacion": "FISICO", "descripcion": "X"},
    )
    assert post_peligro_fantasma.status_code == 404
    assert post_peligro_fantasma.json()["codigo"] == "PROCESO_NO_ENCONTRADO"

    empresa_id = await _crear_empresa(cliente_async, headers)
    proceso_real = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers,
        json={"nombre": "Sin eval", "es_rutinaria": True},
    )
    peligro_real = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso_real.json()['id']}/peligros",
        headers=headers,
        json={"clasificacion": "QUIMICO", "descripcion": "Sin evaluación"},
    )
    evaluacion = await cliente_async.get(
        f"/api/v1/peligros/{peligro_real.json()['id']}/evaluacion",
        headers=headers,
    )
    assert evaluacion.status_code == 404
    assert evaluacion.json()["codigo"] == "EVALUACION_NO_ENCONTRADA"


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


async def test_should_crud_anidado_matriz_when_datos_validos(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    """Cubre listar/obtener/actualizar/eliminar de procesos, peligros y controles."""
    token = await obtener_token(cliente_async, usuarios_semilla)
    headers = bearer(token)
    empresa_id = await _crear_empresa(cliente_async, headers)

    listado_empresas = await cliente_async.get("/api/v1/empresas", headers=headers)
    assert listado_empresas.status_code == 200
    assert any(e["id"] == empresa_id for e in listado_empresas.json())

    proceso = await cliente_async.post(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers,
        json={"nombre": "Pintura", "es_rutinaria": False, "zona_lugar": "Cabina"},
    )
    assert proceso.status_code == 201, proceso.text
    proceso_id = proceso.json()["id"]

    listado = await cliente_async.get(
        f"/api/v1/empresas/{empresa_id}/procesos-actividades",
        headers=headers,
    )
    assert listado.status_code == 200
    assert len(listado.json()) == 1

    detalle = await cliente_async.get(
        f"/api/v1/procesos-actividades/{proceso_id}",
        headers=headers,
    )
    assert detalle.status_code == 200
    assert detalle.json()["nombre"] == "Pintura"

    actualizado = await cliente_async.patch(
        f"/api/v1/procesos-actividades/{proceso_id}",
        headers=headers,
        json={"nombre": "Pintura industrial", "es_rutinaria": True, "zona_lugar": None},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["nombre"] == "Pintura industrial"
    assert actualizado.json()["zona_lugar"] is None

    peligro = await cliente_async.post(
        f"/api/v1/procesos-actividades/{proceso_id}/peligros",
        headers=headers,
        json={
            "clasificacion": "QUIMICO",
            "descripcion": "Vapores de solvente",
            "efectos_posibles": "Irritación",
        },
    )
    assert peligro.status_code == 201, peligro.text
    peligro_id = peligro.json()["id"]

    peligros = await cliente_async.get(
        f"/api/v1/procesos-actividades/{proceso_id}/peligros",
        headers=headers,
    )
    assert peligros.status_code == 200
    assert len(peligros.json()) == 1

    peligro_get = await cliente_async.get(
        f"/api/v1/peligros/{peligro_id}",
        headers=headers,
    )
    assert peligro_get.status_code == 200

    peligro_patch = await cliente_async.patch(
        f"/api/v1/peligros/{peligro_id}",
        headers=headers,
        json={"descripcion": "Vapores de isocianato", "efectos_posibles": None},
    )
    assert peligro_patch.status_code == 200
    assert peligro_patch.json()["descripcion"] == "Vapores de isocianato"

    evaluacion = await cliente_async.put(
        f"/api/v1/peligros/{peligro_id}/evaluacion",
        headers=headers,
        json={
            "nivel_deficiencia": 2,
            "nivel_exposicion": 2,
            "nivel_consecuencia": 25,
        },
    )
    assert evaluacion.status_code == 201, evaluacion.text
    evaluacion_id = evaluacion.json()["id"]

    evaluacion_get = await cliente_async.get(
        f"/api/v1/peligros/{peligro_id}/evaluacion",
        headers=headers,
    )
    assert evaluacion_get.status_code == 200
    assert evaluacion_get.json()["nivel_riesgo"] == 100

    control = await cliente_async.post(
        f"/api/v1/evaluaciones-riesgo/{evaluacion_id}/controles",
        headers=headers,
        json={"tipo": "EPP", "descripcion": "Respirador"},
    )
    assert control.status_code == 201, control.text
    control_id = control.json()["id"]

    controles = await cliente_async.get(
        f"/api/v1/evaluaciones-riesgo/{evaluacion_id}/controles",
        headers=headers,
    )
    assert controles.status_code == 200
    assert len(controles.json()) == 1

    control_patch = await cliente_async.patch(
        f"/api/v1/controles-riesgo/{control_id}",
        headers=headers,
        json={"tipo": "ADMINISTRATIVO", "descripcion": "Rotación de personal"},
    )
    assert control_patch.status_code == 200
    assert control_patch.json()["tipo"] == "ADMINISTRATIVO"

    borrado_control = await cliente_async.delete(
        f"/api/v1/controles-riesgo/{control_id}",
        headers=headers,
    )
    assert borrado_control.status_code == 204

    borrado_peligro = await cliente_async.delete(
        f"/api/v1/peligros/{peligro_id}",
        headers=headers,
    )
    assert borrado_peligro.status_code == 204

    borrado_proceso = await cliente_async.delete(
        f"/api/v1/procesos-actividades/{proceso_id}",
        headers=headers,
    )
    assert borrado_proceso.status_code == 204
