"""Tipos de lectura agregada de la matriz GTC 45 (dominio)."""

from typing import TypedDict

from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad


class NodoPeligroMatriz(TypedDict):
    peligro: Peligro
    evaluacion: EvaluacionRiesgo | None
    controles: list[ControlRiesgo]


class NodoProcesoMatriz(TypedDict):
    proceso: ProcesoActividad
    peligros: list[NodoPeligroMatriz]
