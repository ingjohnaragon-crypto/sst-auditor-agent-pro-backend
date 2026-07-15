"""Router de conectividad ping/pong — valida la comunicación cross-origin con el frontend."""

from fastapi import APIRouter
from fastapi import status as http_status

from src.application.dto import RespuestaPing

router = APIRouter(tags=["Salud"])


@router.get("/ping", status_code=http_status.HTTP_200_OK, response_model=RespuestaPing)
async def ping() -> RespuestaPing:
    """Endpoint de conectividad para validar la comunicación con el frontend."""
    return RespuestaPing(mensaje="pong")
