"""Pruebas del contrato de errores estadísticos SST."""

from src.domain.exceptions.base import DomainException
from src.domain.exceptions.estadisticas_sst import ValorEstadisticoInvalidoError


def test_should_exponer_contrato_dominio_when_valor_estadistico_invalido() -> None:
    mensaje = "El campo horas_trabajadas debe ser mayor que cero"

    error = ValorEstadisticoInvalidoError(mensaje)

    assert isinstance(error, DomainException)
    assert error.code == "VALOR_ESTADISTICO_INVALIDO"
    assert error.http_status == 422
    assert error.message == mensaje
    assert str(error) == mensaje
