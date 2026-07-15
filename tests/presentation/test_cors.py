"""Pruebas de la política CORS registrada sobre la aplicación."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

ORIGEN_PERMITIDO = "http://localhost:4200"


def test_deberia_permitir_origen_configurado_cuando_preflight() -> None:
    response = client.options(
        "/api/v1/ping",
        headers={
            "Origin": ORIGEN_PERMITIDO,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO


def test_deberia_omitir_cabecera_cors_cuando_origen_no_permitido() -> None:
    response = client.options(
        "/api/v1/ping",
        headers={
            "Origin": "http://malicioso.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_deberia_incluir_cabecera_cors_cuando_get_con_origen_permitido() -> None:
    response = client.get("/api/v1/ping", headers={"Origin": ORIGEN_PERMITIDO})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO
    assert response.headers["access-control-allow-credentials"] == "true"
