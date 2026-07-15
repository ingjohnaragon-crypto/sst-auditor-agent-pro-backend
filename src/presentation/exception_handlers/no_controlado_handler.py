"""Manejador global de `Exception` — respuesta 500 genérica sin fuga de información.

El cuerpo de la respuesta nunca incluye la traza, el tipo de excepción ni rutas
de archivos: el detalle completo vive únicamente en el log.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from src.application.dto.respuesta_error import RespuestaError

logger = logging.getLogger(__name__)

MENSAJE_ERROR_INTERNO = "Ha ocurrido un error interno. Contacte al administrador."


async def excepcion_no_controlada_handler(request: Request, exc: Exception) -> JSONResponse:
    """Registra la traza completa y responde 500 con un mensaje genérico."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=RespuestaError(codigo="ERROR_INTERNO", mensaje=MENSAJE_ERROR_INTERNO).model_dump(),
    )
