"""Pruebas de la excepción base del dominio."""

from src.domain.exceptions.base import DomainException


def test_should_use_default_code_and_http_status_when_not_overridden() -> None:
    exc = DomainException("algo salió mal")

    assert exc.message == "algo salió mal"
    assert exc.code == "DOMAIN_ERROR"
    assert exc.http_status == 400
    assert str(exc) == "algo salió mal"


def test_should_override_code_and_http_status_when_provided() -> None:
    exc = DomainException("recurso no encontrado", code="NOT_FOUND", http_status=404)

    assert exc.code == "NOT_FOUND"
    assert exc.http_status == 404
