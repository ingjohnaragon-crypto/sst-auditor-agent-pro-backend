"""Excepciones de dominio del repositorio documental de empresa."""

from src.domain.exceptions.base import DomainException


class ArchivoInvalidoError(DomainException):
    code = "ARCHIVO_INVALIDO"
    http_status = 422

    def __init__(self, message: str = "El archivo no cumple las reglas documentales") -> None:
        super().__init__(message)


class ArchivoNoEncontradoError(DomainException):
    code = "ARCHIVO_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El archivo documental no fue encontrado") -> None:
        super().__init__(message)


class ArchivoObjetoNoDisponibleError(DomainException):
    """Fila presente pero el objeto no está en el almacén (R2)."""

    code = "ARCHIVO_NO_DISPONIBLE"
    http_status = 404

    def __init__(
        self, message: str = "El objeto del archivo documental no está disponible"
    ) -> None:
        super().__init__(message)
