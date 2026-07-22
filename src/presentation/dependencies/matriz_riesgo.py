"""Dependencias FastAPI de la matriz de riesgos GTC 45."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_matriz_riesgos import ServicioMatrizRiesgos
from src.domain.repositories.repositorio_control_riesgo import RepositorioControlRiesgo
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_evaluacion_riesgo import (
    RepositorioEvaluacionRiesgo,
)
from src.domain.repositories.repositorio_peligro import RepositorioPeligro
from src.domain.repositories.repositorio_proceso_actividad import (
    RepositorioProcesoActividad,
)
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_control_riesgo_sqlalchemy import (
    RepositorioControlRiesgoSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_evaluacion_riesgo_sqlalchemy import (
    RepositorioEvaluacionRiesgoSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_peligro_sqlalchemy import (
    RepositorioPeligroSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_proceso_actividad_sqlalchemy import (
    RepositorioProcesoActividadSQLAlchemy,
)
from src.presentation.dependencies.autoevaluacion import obtener_repositorio_empresa


def obtener_repositorio_proceso(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioProcesoActividad:
    return RepositorioProcesoActividadSQLAlchemy(sesion)


def obtener_repositorio_peligro(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioPeligro:
    return RepositorioPeligroSQLAlchemy(sesion)


def obtener_repositorio_evaluacion(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioEvaluacionRiesgo:
    return RepositorioEvaluacionRiesgoSQLAlchemy(sesion)


def obtener_repositorio_control(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioControlRiesgo:
    return RepositorioControlRiesgoSQLAlchemy(sesion)


def obtener_servicio_matriz_riesgos(
    repositorio_empresa: RepositorioEmpresa = Depends(obtener_repositorio_empresa),
    repositorio_proceso: RepositorioProcesoActividad = Depends(obtener_repositorio_proceso),
    repositorio_peligro: RepositorioPeligro = Depends(obtener_repositorio_peligro),
    repositorio_evaluacion: RepositorioEvaluacionRiesgo = Depends(obtener_repositorio_evaluacion),
    repositorio_control: RepositorioControlRiesgo = Depends(obtener_repositorio_control),
) -> ServicioMatrizRiesgos:
    return ServicioMatrizRiesgos(
        repositorio_empresa=repositorio_empresa,
        repositorio_proceso=repositorio_proceso,
        repositorio_peligro=repositorio_peligro,
        repositorio_evaluacion=repositorio_evaluacion,
        repositorio_control=repositorio_control,
    )
