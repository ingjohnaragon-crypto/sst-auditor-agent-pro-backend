"""Excepciones de dominio para metadatos de evidencias."""

from src.domain.exceptions.base import DomainException


class EvidenciaInvalidaError(DomainException):
    code = "EVIDENCIA_INVALIDA"
    http_status = 422

    def __init__(self, message: str = "La evidencia no cumple las reglas de archivo") -> None:
        super().__init__(message)


class EvidenciaNoEncontradaError(DomainException):
    code = "EVIDENCIA_NO_ENCONTRADA"
    http_status = 404

    def __init__(self, message: str = "La evidencia no fue encontrada") -> None:
        super().__init__(message)


class EvidenciaYaInactivaError(DomainException):
    code = "EVIDENCIA_YA_INACTIVA"
    http_status = 409

    def __init__(self, message: str = "La evidencia ya fue dada de baja") -> None:
        super().__init__(message)


class CalificacionNoEncontradaError(DomainException):
    code = "CALIFICACION_NO_ENCONTRADA"
    http_status = 404

    def __init__(self, message: str = "La calificación del estándar no fue encontrada") -> None:
        super().__init__(message)
