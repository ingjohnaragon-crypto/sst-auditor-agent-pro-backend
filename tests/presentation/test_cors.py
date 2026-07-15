"""Pruebas de la política CORS registrada sobre la aplicación."""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from src.infrastructure.config.settings import get_settings
from src.main import app
from src.presentation.routers import api_router

client = TestClient(app)

ORIGEN_PERMITIDO = "http://localhost:4200"
ORIGEN_OVERRIDE = "http://localhost:4300"


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


def test_deberia_respetar_override_origenes_cors_en_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SP-173: ORIGENES_CORS debe cambiar qué orígenes pasan el preflight."""
    monkeypatch.setenv("ORIGENES_CORS", f'["{ORIGEN_OVERRIDE}"]')
    get_settings.cache_clear()

    settings = get_settings()
    app_override = FastAPI()
    app_override.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origenes_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app_override.include_router(api_router)
    client_override = TestClient(app_override)

    permitido = client_override.options(
        "/api/v1/ping",
        headers={
            "Origin": ORIGEN_OVERRIDE,
            "Access-Control-Request-Method": "GET",
        },
    )
    denegado = client_override.options(
        "/api/v1/ping",
        headers={
            "Origin": ORIGEN_PERMITIDO,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert permitido.status_code == 200
    assert permitido.headers["access-control-allow-origin"] == ORIGEN_OVERRIDE
    assert "access-control-allow-origin" not in denegado.headers

    get_settings.cache_clear()
