"""Router de prueba de vida — plantilla de referencia para futuros routers de dominio."""

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.infrastructure.config.settings import Settings, get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=http_status.HTTP_200_OK)
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Verifica que la aplicación y el enrutador raíz están operativos."""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
