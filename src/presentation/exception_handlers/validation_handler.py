"""Manejador global de `RequestValidationError` — traduce errores de validación a JSON."""

import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.application.dto.respuesta_error import RespuestaError

logger = logging.getLogger(__name__)

MENSAJE_VALIDACION = "La petición contiene datos inválidos."


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convierte los errores de validación de Pydantic en la respuesta JSON única de 422."""
    errores = jsonable_encoder(exc.errors())
    logger.warning(
        "Error de validación ERROR_VALIDACION en %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=422,
        content=RespuestaError(
            codigo="ERROR_VALIDACION",
            mensaje=MENSAJE_VALIDACION,
            detalle=errores,
        ).model_dump(),
    )
