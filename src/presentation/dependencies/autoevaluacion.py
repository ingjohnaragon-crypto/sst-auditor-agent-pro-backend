"""Dependencias FastAPI de autoevaluación: repos, servicios y guard escritor."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_autoevaluaciones import ServicioAutoevaluaciones
from src.application.services.servicio_empresas import ServicioEmpresas
from src.domain.exceptions.autoevaluacion import AccesoDenegadoError
from src.domain.models.usuario import RolUsuario, Usuario
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_autoevaluacion_sqlalchemy import (
    RepositorioAutoevaluacionSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_empresa_sqlalchemy import (
    RepositorioEmpresaSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_estandar_minimo_sqlalchemy import (
    RepositorioEstandarMinimoSQLAlchemy,
)
from src.presentation.dependencies.autenticacion import obtener_usuario_actual


def obtener_repositorio_empresa(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioEmpresa:
    """Ensambla la implementación SQLAlchemy del repositorio de empresas."""
    return RepositorioEmpresaSQLAlchemy(sesion)


def obtener_repositorio_estandar_minimo(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioEstandarMinimo:
    """Ensambla la implementación SQLAlchemy del catálogo de estándares."""
    return RepositorioEstandarMinimoSQLAlchemy(sesion)


def obtener_repositorio_autoevaluacion(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioAutoevaluacion:
    """Ensambla la implementación SQLAlchemy del agregado autoevaluación."""
    return RepositorioAutoevaluacionSQLAlchemy(sesion)


def obtener_servicio_empresas(
    repositorio: RepositorioEmpresa = Depends(obtener_repositorio_empresa),
) -> ServicioEmpresas:
    """Ensambla el servicio de empresas con su puerto de persistencia."""
    return ServicioEmpresas(repositorio=repositorio)


def obtener_servicio_autoevaluaciones(
    repositorio_autoevaluacion: RepositorioAutoevaluacion = Depends(
        obtener_repositorio_autoevaluacion
    ),
    repositorio_empresa: RepositorioEmpresa = Depends(obtener_repositorio_empresa),
    repositorio_estandar_minimo: RepositorioEstandarMinimo = Depends(
        obtener_repositorio_estandar_minimo
    ),
) -> ServicioAutoevaluaciones:
    """Ensambla el servicio de autoevaluaciones con sus tres puertos."""
    return ServicioAutoevaluaciones(
        repositorio_autoevaluacion=repositorio_autoevaluacion,
        repositorio_empresa=repositorio_empresa,
        repositorio_estandar_minimo=repositorio_estandar_minimo,
    )


async def requerir_rol_escritor(
    usuario: Usuario = Depends(obtener_usuario_actual),
) -> Usuario:
    """Exige rol distinto de CONSULTA; emite `ACCESO_DENEGADO` (403)."""
    if usuario.rol == RolUsuario.CONSULTA:
        raise AccesoDenegadoError()
    return usuario
