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

MENSAJE_HTTP_GENERICO = "La petición HTTP no pudo completarse."


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Convierte cualquier `HTTPException` en la respuesta JSON única, conservando su status."""
    logger.warning(
        "Error HTTP %s (ERROR_HTTP) en %s %s", exc.status_code, request.method, request.url.path
    )
    # FastAPI permite `detail` no textual (dict, list, etc.); un str(...) directo
    # produciría un repr de Python en `mensaje`, así que lo enviamos en `detalle`.
    detalle_crudo: object = exc.detail
    if isinstance(detalle_crudo, str):
        respuesta = RespuestaError(codigo="ERROR_HTTP", mensaje=detalle_crudo)
    elif isinstance(detalle_crudo, dict | list):
        respuesta = RespuestaError(
            codigo="ERROR_HTTP", mensaje=MENSAJE_HTTP_GENERICO, detalle=detalle_crudo
        )
    else:
        respuesta = RespuestaError(codigo="ERROR_HTTP", mensaje=str(detalle_crudo))
    return JSONResponse(status_code=exc.status_code, content=respuesta.model_dump())
