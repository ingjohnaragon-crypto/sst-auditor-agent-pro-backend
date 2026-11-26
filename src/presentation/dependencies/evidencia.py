"""Dependencias FastAPI de evidencias."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_carga_evidencia import (
    AlmacenEvidencias,
    ServicioCargaEvidencia,
)
from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.application.services.servicio_evidencias import ServicioEvidencias
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.almacenamiento.almacen_r2 import crear_almacen_r2
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


def obtener_almacen_evidencias() -> AlmacenEvidencias:
    """Almacén de producción (R2) o doble vacío si R2 no está configurado."""
    settings = get_settings()
    if settings.r2_configurado:
        return crear_almacen_r2(settings)
    return AlmacenMemoria()


def obtener_servicio_descarga_evidencia(
    repositorio_evidencia: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
    repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
    repositorio_acceso: RepositorioAccesoEvidencia = Depends(obtener_repositorio_acceso_evidencia),
    servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
    almacen: AlmacenEvidencias = Depends(obtener_almacen_evidencias),
) -> ServicioDescargaEvidencia:
    """Ensambla el caso de uso de enlace y canje de descarga."""
    settings = get_settings()
    return ServicioDescargaEvidencia(
        repositorio_evidencia=repositorio_evidencia,
        repositorio_usuario=repositorio_usuario,
        repositorio_acceso=repositorio_acceso,
        servicio_tokens=servicio_tokens,
        almacen=almacen,
        segundos_expiracion=settings.descarga_segundos_expiracion,
        prefijo_api=settings.api_prefix,
    )


def obtener_servicio_carga_evidencia(
    repositorio: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
    almacen: AlmacenEvidencias = Depends(obtener_almacen_evidencias),
) -> ServicioCargaEvidencia:
    """Ensambla la carga multipart con el almacén R2 configurado."""
    settings = get_settings()
    return ServicioCargaEvidencia(
        repositorio=repositorio,
        almacen=almacen,
        r2_configurado=settings.r2_configurado,
    )
