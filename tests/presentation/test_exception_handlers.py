"""Pruebas de los manejadores globales de excepciones registrados sobre la app."""

import logging

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from src.domain.exceptions.base import DomainException
from src.presentation.exception_handlers import registrar_manejadores_excepciones


class _CargaDePrueba(BaseModel):
    name: str


def _construir_app_de_prueba() -> FastAPI:
    test_app = FastAPI()
    registrar_manejadores_excepciones(test_app)

    router = APIRouter()

    @router.get("/lanzar-error-dominio")
    async def lanzar_error_dominio() -> None:
        raise DomainException("recurso no encontrado", code="NOT_FOUND", http_status=404)

    @router.get("/lanzar-error-dominio-por-defecto")
    async def lanzar_error_dominio_por_defecto() -> None:
        raise DomainException("regla de negocio violada")

    @router.post("/validar")
    async def validar(payload: _CargaDePrueba) -> _CargaDePrueba:
        return payload

    @router.get("/lanzar-error-interno")
    async def lanzar_error_interno() -> None:
        raise RuntimeError("secreto interno")

    test_app.include_router(router)
    return test_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_construir_app_de_prueba(), raise_server_exceptions=False)


def test_should_devolver_esquema_error_cuando_se_lanza_domain_exception(
    client: TestClient,
) -> None:
    response = client.get("/lanzar-error-dominio")

    assert response.status_code == 404
    assert response.json() == {
        "exito": False,
        "codigo": "NOT_FOUND",
        "mensaje": "recurso no encontrado",
        "detalle": None,
    }


def test_should_devolver_error_dominio_por_defecto_cuando_no_se_da_codigo(
    client: TestClient,
) -> None:
    response = client.get("/lanzar-error-dominio-por-defecto")

    assert response.status_code == 400
    assert response.json() == {
        "exito": False,
        "codigo": "ERROR_DOMINIO",
        "mensaje": "regla de negocio violada",
        "detalle": None,
    }


def test_should_devolver_error_validacion_cuando_payload_es_invalido(
    client: TestClient,
) -> None:
    response = client.post("/validar", json={})

    body = response.json()
    assert response.status_code == 422
    assert body["exito"] is False
    assert body["codigo"] == "ERROR_VALIDACION"
    assert body["mensaje"] == "La petición contiene datos inválidos."
    assert isinstance(body["detalle"], list)
    assert len(body["detalle"]) > 0


def test_should_devolver_esquema_error_cuando_ruta_no_existe(
    client: TestClient,
) -> None:
    response = client.get("/no-existe")

    body = response.json()
    assert response.status_code == 404
    assert body["exito"] is False
    assert body["codigo"] == "ERROR_HTTP"
    assert isinstance(body["mensaje"], str)
    assert body["detalle"] is None


def test_should_devolver_500_generico_cuando_excepcion_no_controlada(
    client: TestClient,
) -> None:
    response = client.get("/lanzar-error-interno")

    assert response.status_code == 500
    assert response.json() == {
        "exito": False,
        "codigo": "ERROR_INTERNO",
        "mensaje": "Ha ocurrido un error interno. Contacte al administrador.",
        "detalle": None,
    }


def test_should_no_exponer_traza_en_respuesta_cuando_falla_interno(
    client: TestClient,
) -> None:
    response = client.get("/lanzar-error-interno")

    cuerpo = response.text
    assert "Traceback" not in cuerpo
    assert "RuntimeError" not in cuerpo
    assert "secreto interno" not in cuerpo
    assert ".py" not in cuerpo


def test_should_registrar_traza_cuando_excepcion_no_controlada(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        client.get("/lanzar-error-interno")

    registros = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(registros) == 1
    assert "GET" in registros[0].getMessage()
    assert "/lanzar-error-interno" in registros[0].getMessage()
    assert registros[0].exc_info is not None
    assert "RuntimeError" in caplog.text


def test_should_registrar_warning_cuando_error_de_dominio(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        client.get("/lanzar-error-dominio")

    registros = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(registros) == 1
    assert "NOT_FOUND" in registros[0].getMessage()
    assert registros[0].exc_info is None
