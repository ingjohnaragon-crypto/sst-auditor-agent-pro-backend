"""Punto de entrada de la aplicación — instancia FastAPI y monta el router raíz."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.configuracion_logging import configurar_logging
from src.infrastructure.config.settings import get_settings
from src.presentation.exception_handlers import registrar_manejadores_excepciones
from src.presentation.routers import api_router

settings = get_settings()
configurar_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)

# Los orígenes provienen exclusivamente de Settings — nunca usar "*" con credenciales.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registrar_manejadores_excepciones(app)

app.include_router(api_router)
