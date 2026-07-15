"""Pruebas del endpoint de conectividad ping/pong."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_deberia_responder_pong_cuando_se_consulta_ping() -> None:
    response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"mensaje": "pong"}


def test_deberia_responder_404_cuando_falta_el_prefijo() -> None:
    response = client.get("/ping")

    body = response.json()
    assert response.status_code == 404
    assert body["exito"] is False
    assert body["codigo"] == "ERROR_HTTP"


def test_deberia_responder_405_cuando_metodo_no_soportado() -> None:
    response = client.post("/api/v1/ping")

    body = response.json()
    assert response.status_code == 405
    assert body["exito"] is False
    assert body["codigo"] == "ERROR_HTTP"


def test_deberia_documentar_ping_bajo_tag_salud() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/ping" in paths
    assert paths["/api/v1/ping"]["get"]["tags"] == ["Salud"]
