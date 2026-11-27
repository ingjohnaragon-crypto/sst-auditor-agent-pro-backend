"""Excepciones de dominio del catálogo documental PHVA."""

from src.domain.exceptions.base import DomainException


class DocumentoInvalidoError(DomainException):
    code = "DOCUMENTO_INVALIDO"
    http_status = 422

    def __init__(self, message: str = "El documento no cumple las reglas del catálogo") -> None:
        super().__init__(message)


class DocumentoNoEncontradoError(DomainException):
    code = "DOCUMENTO_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El documento de empresa no fue encontrado") -> None:
        super().__init__(message)


class TipoDocumentoNoEncontradoError(DomainException):
    code = "TIPO_DOCUMENTO_NO_ENCONTRADO"
    http_status = 404

    def __init__(self, message: str = "El tipo de documento no fue encontrado") -> None:
        super().__init__(message)


class DocumentoEstadoInvalidoError(DomainException):
    code = "CONFLICTO_ESTADO_DOCUMENTO"
    http_status = 409

    def __init__(
        self,
        message: str = "La transición de estado del documento no está permitida",
    ) -> None:
        super().__init__(message)


class DocumentoObjetoNoDisponibleError(DomainException):
    code = "DOCUMENTO_NO_DISPONIBLE"
    http_status = 404

    def __init__(
        self, message: str = "El objeto del documento no está disponible en el almacén"
    ) -> None:
        super().__init__(message)
