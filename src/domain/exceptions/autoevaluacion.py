"""Excepciones de dominio para empresas y autoevaluación Res. 0312."""

from src.domain.exceptions.base import DomainException


class EmpresaNoEncontradaError(DomainException):
    code = "EMPRESA_NO_ENCONTRADA"
    http_status = 404

    def __init__(self, message: str = "La empresa no fue encontrada") -> None:
        super().__init__(message)


class NitDuplicadoError(DomainException):
    code = "NIT_DUPLICADO"
    http_status = 409

    def __init__(self, message: str = "Ya existe una empresa con ese NIT") -> None:
        super().__init__(message)


class AutoevaluacionNoEncontradaError(DomainException):
    code = "AUTOEVALUACION_NO_ENCONTRADA"
    http_status = 404

    def __init__(self, message: str = "La autoevaluación no fue encontrada") -> None:
        super().__init__(message)


class EstandarNoEncontradoError(DomainException):
    code = "ESTANDAR_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El estándar mínimo no fue encontrado") -> None:
        super().__init__(message)


class AutoevaluacionIncompletaError(DomainException):
    code = "AUTOEVALUACION_INCOMPLETA"
    http_status = 409

    def __init__(
        self,
        message: str = "La autoevaluación no tiene todos los estándares calificados",
        *,
        faltantes: int | None = None,
    ) -> None:
        super().__init__(message)
        self.faltantes = faltantes


class AutoevaluacionFinalizadaError(DomainException):
    code = "AUTOEVALUACION_FINALIZADA"
    http_status = 409

    def __init__(
        self, message: str = "La autoevaluación ya está finalizada y no admite cambios"
    ) -> None:
        super().__init__(message)


class AccesoDenegadoError(DomainException):
    code = "ACCESO_DENEGADO"
    http_status = 403

    def __init__(self, message: str = "No tiene permisos para realizar esta acción") -> None:
        super().__init__(message)


class DatosEmpresaInvalidosError(DomainException):
    code = "DATOS_EMPRESA_INVALIDOS"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
