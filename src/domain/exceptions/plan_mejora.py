"""Excepciones de dominio del plan de mejora y su cronograma."""

from src.domain.exceptions.base import DomainException


class AutoevaluacionEnBorradorError(DomainException):
    code = "AUTOEVALUACION_EN_BORRADOR"
    http_status = 409

    def __init__(
        self,
        message: str = "La autoevaluación está en borrador y no admite plan de mejora",
    ) -> None:
        super().__init__(message)


class PlanMejoraNoRequeridoError(DomainException):
    code = "PLAN_MEJORA_NO_REQUERIDO"
    http_status = 409

    def __init__(
        self,
        message: str = "La autoevaluación no requiere plan de mejora",
    ) -> None:
        super().__init__(message)


class AutoevaluacionSinPersistirError(DomainException):
    code = "AUTOEVALUACION_SIN_PERSISTIR"
    http_status = 409

    def __init__(
        self,
        message: str = "La autoevaluación aún no está persistida",
    ) -> None:
        super().__init__(message)


class ActividadCronogramaInvalidaError(DomainException):
    code = "ACTIVIDAD_CRONOGRAMA_INVALIDA"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
