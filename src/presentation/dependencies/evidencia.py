"""Dependencias FastAPI de evidencias."""

from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.application.services.servicio_evidencias import ServicioEvidencias
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_acceso_evidencia_sqlalchemy import (
    RepositorioAccesoEvidenciaSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_evidencia_sqlalchemy import (
    RepositorioEvidenciaSQLAlchemy,
)
from src.presentation.dependencies.autenticacion import (
    obtener_repositorio_usuario,
    obtener_servicio_tokens,
)


def obtener_repositorio_evidencia(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioEvidencia:
    """Ensambla la implementación SQLAlchemy del repositorio de evidencias."""
    return RepositorioEvidenciaSQLAlchemy(sesion)


def obtener_servicio_evidencias(
    repositorio: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
) -> ServicioEvidencias:
    """Ensambla el servicio de evidencias con su puerto de persistencia."""
    return ServicioEvidencias(repositorio=repositorio)


def obtener_repositorio_acceso_evidencia(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioAccesoEvidencia:
    """Ensambla la implementación SQLAlchemy de la auditoría de descargas."""
    return RepositorioAccesoEvidenciaSQLAlchemy(sesion)


def obtener_raiz_almacenamiento() -> Path | None:
    """Directorio de binarios. Vacío si la variable no está definida."""
    valor = get_settings().almacenamiento_local_raiz
    if not valor:
        return None
    return Path(valor)


def obtener_servicio_descarga_evidencia(
    repositorio_evidencia: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
    repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    repositorio_acceso: RepositorioAccesoEvidencia = Depends(obtener_repositorio_acceso_evidencia),
    servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
    raiz: Path | None = Depends(obtener_raiz_almacenamiento),
) -> ServicioDescargaEvidencia:
    """Ensambla el caso de uso de enlace y canje de descarga."""
    settings = get_settings()
    return ServicioDescargaEvidencia(
        repositorio_evidencia=repositorio_evidencia,
        repositorio_usuario=repositorio_usuario,
        repositorio_acceso=repositorio_acceso,
        servicio_tokens=servicio_tokens,
        segundos_expiracion=settings.descarga_segundos_expiracion,
        prefijo_api=settings.api_prefix,
        raiz_almacenamiento=raiz,
    )
