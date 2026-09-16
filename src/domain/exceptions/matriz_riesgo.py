"""Excepciones de dominio para la matriz de riesgos GTC 45."""

from src.domain.exceptions.base import DomainException


class ProcesoNoEncontradoError(DomainException):
    code = "PROCESO_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El proceso/actividad no fue encontrado") -> None:
        super().__init__(message)


class PeligroNoEncontradoError(DomainException):
    code = "PELIGRO_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El peligro no fue encontrado") -> None:
        super().__init__(message)


class EvaluacionNoEncontradaError(DomainException):
    code = "EVALUACION_NO_ENCONTRADA"
    http_status = 404

    def __init__(self, message: str = "La evaluación de riesgo no fue encontrada") -> None:
        super().__init__(message)


class ControlNoEncontradoError(DomainException):
    code = "CONTROL_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El control de riesgo no fue encontrado") -> None:
        super().__init__(message)


class ValorGtcInvalidoError(DomainException):
    code = "VALOR_GTC_INVALIDO"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatosProcesoInvalidosError(DomainException):
    code = "DATOS_PROCESO_INVALIDOS"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatosPeligroInvalidosError(DomainException):
    code = "DATOS_PELIGRO_INVALIDOS"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatosControlInvalidosError(DomainException):
    code = "DATOS_CONTROL_INVALIDOS"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
