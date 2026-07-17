"""Pruebas de la factoría e invariantes de `Empresa`."""

import pytest
from src.domain.exceptions.autoevaluacion import DatosEmpresaInvalidosError
from src.domain.models.empresa import Empresa


def test_should_crear_empresa_when_datos_validos() -> None:
    empresa = Empresa.crear(
        razon_social=" Acme SST ",
        nit="900123456-1",
        actividad_economica="Consultoría",
        nivel_riesgo_arl="iii",
        numero_trabajadores=10,
    )

    assert empresa.razon_social == "Acme SST"
    assert empresa.nit == "900123456-1"
    assert empresa.nivel_riesgo_arl == "III"
    assert empresa.id is None


def test_should_lanzar_error_when_numero_trabajadores_no_positivo() -> None:
    with pytest.raises(DatosEmpresaInvalidosError, match="trabajadores"):
        Empresa.crear("Acme", "900", "Actividad", "I", 0)


def test_should_lanzar_error_when_nivel_riesgo_invalido() -> None:
    with pytest.raises(DatosEmpresaInvalidosError, match="nivel de riesgo"):
        Empresa.crear("Acme", "900", "Actividad", "VI", 5)


def test_should_lanzar_error_when_nit_vacio() -> None:
    with pytest.raises(DatosEmpresaInvalidosError, match="NIT"):
        Empresa.crear("Acme", "  ", "Actividad", "I", 5)
