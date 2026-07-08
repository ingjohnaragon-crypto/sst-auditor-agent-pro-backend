"""Manejador global de `HTTPException` — traduce errores HTTP genéricos a JSON.

Se registra sobre la clase de Starlette para capturar también los 404/405 que
genera el propio enrutador; `fastapi.HTTPException` es subclase y queda cubierta.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.application.dto.respuesta_error import RespuestaError

logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Convierte cualquier `HTTPException` en la respuesta JSON única, conservando su status."""
    logger.warning(
        "Error HTTP %s ERROR_HTTP en %s %s", exc.status_code, request.method, request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=RespuestaError(codigo="ERROR_HTTP", mensaje=str(exc.detail)).model_dump(),
    )
