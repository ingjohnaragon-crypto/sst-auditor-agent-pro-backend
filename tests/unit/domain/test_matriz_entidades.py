"""Pruebas de factorías de proceso, peligro y control."""

from uuid import uuid4

import pytest
from src.domain.exceptions.matriz_riesgo import (
    DatosControlInvalidosError,
    DatosPeligroInvalidosError,
    DatosProcesoInvalidosError,
)
from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.gtc45 import ClasificacionPeligro, TipoControl
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad


def test_should_crear_proceso_when_nombre_valido() -> None:
    proceso = ProcesoActividad.crear(uuid4(), "  Soldadura  ", True, "Planta 1")
    assert proceso.nombre == "Soldadura"
    assert proceso.es_rutinaria is True
    assert proceso.zona_lugar == "Planta 1"


def test_should_lanzar_when_nombre_proceso_vacio() -> None:
    with pytest.raises(DatosProcesoInvalidosError):
        ProcesoActividad.crear(uuid4(), "  ", False)


def test_should_crear_peligro_when_clasificacion_valida() -> None:
    peligro = Peligro.crear(uuid4(), "fisico", "Ruido", "Hipoacusia")
    assert peligro.clasificacion == ClasificacionPeligro.FISICO
    assert peligro.descripcion == "Ruido"


def test_should_lanzar_when_clasificacion_invalida() -> None:
    with pytest.raises(DatosPeligroInvalidosError):
        Peligro.crear(uuid4(), "OTRO", "x")


def test_should_crear_control_when_tipo_valido() -> None:
    control = ControlRiesgo.crear(uuid4(), "ingenieria", "Barrera acústica")
    assert control.tipo == TipoControl.INGENIERIA


def test_should_lanzar_when_tipo_control_invalido() -> None:
    with pytest.raises(DatosControlInvalidosError):
        ControlRiesgo.crear(uuid4(), "NINGUNO", "x")
