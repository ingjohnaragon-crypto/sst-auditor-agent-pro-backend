"""Punto de entrada de la aplicación — instancia FastAPI y monta el router raíz."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.domain.exceptions.base import DomainException
from src.infrastructure.config.settings import get_settings
from src.presentation.exception_handlers.domain_handler import domain_exception_handler
from src.presentation.exception_handlers.validation_handler import (
    validation_exception_handler,
)
from src.presentation.routers import api_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.exception_handler(DomainException)(domain_exception_handler)
app.exception_handler(RequestValidationError)(validation_exception_handler)

app.include_router(api_router)
