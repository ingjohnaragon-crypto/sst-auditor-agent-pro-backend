"""Pruebas del router de prueba de vida y de su registro en el router agregador."""

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from src.infrastructure.config.settings import get_settings
from src.main import app
from src.presentation.routers import api_router

client = TestClient(app)


def test_should_return_ok_status_when_health_endpoint_is_called() -> None:
    settings = get_settings()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


def test_should_register_health_router_in_aggregator_router() -> None:
    paths = [route.path for route in api_router.routes if isinstance(route, APIRoute)]

    assert "/health" in paths
