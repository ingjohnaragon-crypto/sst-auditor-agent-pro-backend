"""Manejador global de `DomainException` — traduce errores de dominio a JSON."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from src.application.dto.respuesta_error import RespuestaError
from src.domain.exceptions.base import DomainException

logger = logging.getLogger(__name__)


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Convierte cualquier `DomainException` en la respuesta JSON única de error."""
    logger.warning("Error de dominio %s en %s %s", exc.code, request.method, request.url.path)
    return JSONResponse(
        status_code=exc.http_status,
        content=RespuestaError(codigo=exc.code, mensaje=exc.message).model_dump(),
    )
