"""Pruebas de los manejadores globales de excepciones registrados sobre la app."""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from src.domain.exceptions.base import DomainException
from src.presentation.exception_handlers.domain_handler import domain_exception_handler
from src.presentation.exception_handlers.validation_handler import (
    validation_exception_handler,
)


class _SamplePayload(BaseModel):
    name: str


def _build_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.exception_handler(DomainException)(domain_exception_handler)
    test_app.exception_handler(RequestValidationError)(validation_exception_handler)

    router = APIRouter()

    @router.get("/raise-domain-error")
    async def raise_domain_error() -> None:
        raise DomainException("recurso no encontrado", code="NOT_FOUND", http_status=404)

    @router.post("/validate")
    async def validate(payload: _SamplePayload) -> _SamplePayload:
        return payload

    test_app.include_router(router)
    return test_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_test_app())


def test_should_return_domain_error_payload_when_domain_exception_is_raised(
    client: TestClient,
) -> None:
    response = client.get("/raise-domain-error")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "code": "NOT_FOUND",
        "message": "recurso no encontrado",
    }


def test_should_return_validation_error_payload_when_payload_is_invalid(
    client: TestClient,
) -> None:
    response = client.post("/validate", json={})

    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["details"], list)
    assert len(body["details"]) > 0
