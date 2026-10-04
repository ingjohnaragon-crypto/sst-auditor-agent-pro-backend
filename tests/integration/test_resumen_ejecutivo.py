"""Integración HTTP del resumen ejecutivo."""

from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM

from tests.integration.conftest import UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

_PAYLOAD = {
    "razon_social": "Empresa Resumen SA",
    "nit": "901253000-1",
    "actividad_economica": "Servicios",
    "nivel_riesgo_arl": "II",
    "numero_trabajadores": 8,
}


def _assert_error(body: dict[str, object], codigo: str) -> None:
    assert body["exito"] is False
    assert body["codigo"] == codigo


async def _sembrar_irrenunciables(cliente: AsyncClient) -> None:
    fabrica = cliente.fabrica_sesion  # type: ignore[attr-defined]
    async with fabrica() as sesion:
        sesion.add(
            EstandarMinimoORM(
                ciclo_phva="PLANEAR",
                numeral="1.1.1",
                descripcion="Responsable del SG-SST",
                valor_porcentual=Decimal("0.50"),
            )
        )
        sesion.add(
            EstandarMinimoORM(
                ciclo_phva="PLANEAR",
                numeral="1.1.4",
                descripcion="Afiliación al sistema de riesgos laborales",
                valor_porcentual=Decimal("0.50"),
            )
        )
        await sesion.commit()


async def test_should_leer_resumen_vacio_when_consulta(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    await _sembrar_irrenunciables(cliente_async)
    token_admin = await obtener_token(cliente_async, usuarios_semilla)
    creada = await cliente_async.post(
        "/api/v1/empresas",
        headers=bearer(token_admin),
        json=_PAYLOAD,
    )
    assert creada.status_code == 201
    empresa_id = creada.json()["id"]

    token_consulta = await obtener_token(
        cliente_async,
        usuarios_semilla,
        correo=usuarios_semilla.correo_consulta,
    )
    respuesta = await cliente_async.get(
        f"/api/v1/empresas/{empresa_id}/resumen-ejecutivo",
        headers=bearer(token_consulta),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cantidad_autoevaluaciones"] == 0
    assert cuerpo["autoevaluacion_id"] is None
    assert cuerpo["requiere_plan_mejora"] is False
    assert cuerpo["distribucion_riesgos"] == {"I": 0, "II": 0, "III": 0, "IV": 0}
    assert cuerpo["riesgos_nivel_i"] == 0
    assert [item["resultado"] for item in cuerpo["irrenunciables"]] == [
        "SIN_CALIFICAR",
        "SIN_CALIFICAR",
    ]


async def test_should_responder_401_when_no_hay_token(cliente_async: AsyncClient) -> None:
    respuesta = await cliente_async.get(f"/api/v1/empresas/{uuid4()}/resumen-ejecutivo")
    assert respuesta.status_code == 401
    _assert_error(respuesta.json(), "TOKEN_INVALIDO")


async def test_should_responder_404_when_empresa_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    token = await obtener_token(
        cliente_async,
        usuarios_semilla,
        correo=usuarios_semilla.correo_consulta,
    )
    respuesta = await cliente_async.get(
        f"/api/v1/empresas/{uuid4()}/resumen-ejecutivo",
        headers=bearer(token),
    )
    assert respuesta.status_code == 404
    _assert_error(respuesta.json(), "EMPRESA_NO_ENCONTRADA")
