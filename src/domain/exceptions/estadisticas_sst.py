"""Excepciones de dominio para cálculos estadísticos del SG-SST."""

from src.domain.exceptions.base import DomainException


class ValorEstadisticoInvalidoError(DomainException):
    """Indica que un cálculo recibió un valor fuera de su dominio válido."""

    code = "VALOR_ESTADISTICO_INVALIDO"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
