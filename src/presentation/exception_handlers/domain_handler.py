"""Manejador global de `DomainException` — traduce errores de dominio a JSON."""

from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.exceptions.base import DomainException


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Convierte cualquier `DomainException` no controlada en una respuesta JSON uniforme."""
    return JSONResponse(
        status_code=exc.http_status,
        content={"success": False, "code": exc.code, "message": exc.message},
    )
