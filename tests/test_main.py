"""Pruebas de arranque de la aplicación."""

from fastapi.testclient import TestClient
from src.main import app


def test_should_start_application_without_errors_when_only_health_router_is_registered() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200


def test_should_serve_swagger_docs() -> None:
    client = TestClient(app)

    response = client.get("/docs")

    assert response.status_code == 200


def test_should_serve_redoc_docs() -> None:
    client = TestClient(app)

    response = client.get("/redoc")

    assert response.status_code == 200
