"""Registro centralizado de los manejadores globales de excepciones."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.exceptions.base import DomainException
from src.presentation.exception_handlers.domain_handler import domain_exception_handler
from src.presentation.exception_handlers.http_handler import http_exception_handler
from src.presentation.exception_handlers.no_controlado_handler import (
    excepcion_no_controlada_handler,
)
from src.presentation.exception_handlers.validation_handler import (
    validation_exception_handler,
)

__all__ = ["registrar_manejadores_excepciones"]


def registrar_manejadores_excepciones(app: FastAPI) -> None:
    """Registra los cuatro manejadores globales de excepciones sobre la app.

    Se usa la forma decorador `app.exception_handler(...)` porque la firma de
    `add_exception_handler` exige `Callable[[Request, Exception], Response]` y
    rechazaría bajo mypy strict los manejadores tipados con excepciones concretas.
    """
    app.exception_handler(DomainException)(domain_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(StarletteHTTPException)(http_exception_handler)
    app.exception_handler(Exception)(excepcion_no_controlada_handler)
