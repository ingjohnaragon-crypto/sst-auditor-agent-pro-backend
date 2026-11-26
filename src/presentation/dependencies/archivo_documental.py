"""Dependencias FastAPI del repositorio documental de empresa."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_archivos_documentales import (
    ServicioArchivosDocumentales,
)
from src.application.services.servicio_carga_evidencia import AlmacenEvidencias
from src.domain.repositories.repositorio_archivo_documental import (
    RepositorioArchivoDocumental,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.almacenamiento.almacen_r2 import crear_almacen_r2
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_archivo_documental_sqlalchemy import (
    RepositorioArchivoDocumentalSQLAlchemy,
)
from src.presentation.dependencies.autenticacion import obtener_repositorio_usuario


def obtener_repositorio_archivo_documental(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioArchivoDocumental:
    """Ensambla la implementación SQLAlchemy del repositorio documental."""
    return RepositorioArchivoDocumentalSQLAlchemy(sesion)


def obtener_almacen_archivos() -> AlmacenEvidencias:
    """Almacén de producción (R2) o doble vacío si R2 no está configurado.

    Si faltan variables, no se construye el cliente: el servicio corta con 503
    antes de llamar al almacén.
    """
    settings = get_settings()
    if settings.r2_configurado:
        return crear_almacen_r2(settings)
    return AlmacenMemoria()


def obtener_servicio_archivos_documentales(
    repositorio: RepositorioArchivoDocumental = Depends(obtener_repositorio_archivo_documental),
    almacen: AlmacenEvidencias = Depends(obtener_almacen_archivos),
    repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
) -> ServicioArchivosDocumentales:
    """Ensambla el caso de uso documental con el almacén configurado."""
    settings = get_settings()
    return ServicioArchivosDocumentales(
        repositorio=repositorio,
        almacen=almacen,
        repositorio_usuario=repositorio_usuario,
        r2_configurado=settings.r2_configurado,
    )
