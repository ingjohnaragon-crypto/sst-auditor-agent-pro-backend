"""Dependencias FastAPI de evidencias."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_evidencias import ServicioEvidencias
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_evidencia_sqlalchemy import (
    RepositorioEvidenciaSQLAlchemy,
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
