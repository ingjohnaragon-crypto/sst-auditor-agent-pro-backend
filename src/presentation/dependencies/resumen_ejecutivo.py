"""Dependencia FastAPI del resumen ejecutivo.

Vive aparte de `autoevaluacion.py` para no importar en círculo con `matriz_riesgo.py`.
"""

from fastapi import Depends

from src.application.services.servicio_resumen_ejecutivo import ServicioResumenEjecutivo
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.domain.repositories.repositorio_proceso_actividad import RepositorioProcesoActividad
from src.presentation.dependencies.autoevaluacion import (
    obtener_repositorio_autoevaluacion,
    obtener_repositorio_empresa,
    obtener_repositorio_estandar_minimo,
)
from src.presentation.dependencies.matriz_riesgo import obtener_repositorio_proceso


def obtener_servicio_resumen_ejecutivo(
    repositorio_empresa: RepositorioEmpresa = Depends(obtener_repositorio_empresa),
    repositorio_autoevaluacion: RepositorioAutoevaluacion = Depends(
        obtener_repositorio_autoevaluacion
    ),
    repositorio_estandar_minimo: RepositorioEstandarMinimo = Depends(
        obtener_repositorio_estandar_minimo
    ),
    repositorio_proceso: RepositorioProcesoActividad = Depends(obtener_repositorio_proceso),
) -> ServicioResumenEjecutivo:
    """Ensambla el caso de uso con los puertos ya existentes."""
    return ServicioResumenEjecutivo(
        repositorio_empresa=repositorio_empresa,
        repositorio_autoevaluacion=repositorio_autoevaluacion,
        repositorio_estandar_minimo=repositorio_estandar_minimo,
        repositorio_proceso=repositorio_proceso,
    )
