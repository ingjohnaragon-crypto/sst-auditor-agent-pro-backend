"""Router agregador — centraliza el registro de subrouters por dominio.

Para añadir un nuevo dominio (por ejemplo `audits`), basta con:
1. Crear `src/presentation/routers/audits_router.py` con su propio `APIRouter`.
2. Añadir una línea de `include_router` aquí abajo, con su prefijo y tags:

    from src.presentation.routers.audits_router import router as audits_router
    api_router.include_router(
        audits_router, prefix=f"{settings.api_prefix}/audits", tags=["Audits"]
    )

No es necesario modificar `src/main.py`.
"""

from fastapi import APIRouter

from src.presentation.routers.health_router import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
