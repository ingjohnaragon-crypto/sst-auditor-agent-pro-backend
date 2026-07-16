"""Excepciones de dominio para autenticación y autorización."""

from src.domain.exceptions.base import DomainException

# Mensaje único para cualquier fallo de credenciales (correo inexistente,
# contraseña incorrecta o usuario inactivo) — no revelar cuál falló.
MENSAJE_CREDENCIALES_INVALIDAS = "Correo o contraseña incorrectos"
MENSAJE_TOKEN_INVALIDO = "El token no es válido"
MENSAJE_TOKEN_EXPIRADO = "El token ha expirado"
MENSAJE_PERMISOS_INSUFICIENTES = "No tiene permisos para acceder a este recurso"


class CredencialesInvalidasException(DomainException):
    """Credenciales de inicio de sesión inválidas (401)."""

    code = "CREDENCIALES_INVALIDAS"
    http_status = 401

    def __init__(self, message: str = MENSAJE_CREDENCIALES_INVALIDAS) -> None:
        super().__init__(message)


class TokenInvalidoException(DomainException):
    """Token mal firmado, corrupto o de tipo incorrecto (401)."""

    code = "TOKEN_INVALIDO"
    http_status = 401

    def __init__(self, message: str = MENSAJE_TOKEN_INVALIDO) -> None:
        super().__init__(message)


class TokenExpiradoException(DomainException):
    """Token con la fecha de expiración vencida (401)."""

    code = "TOKEN_EXPIRADO"
    http_status = 401

    def __init__(self, message: str = MENSAJE_TOKEN_EXPIRADO) -> None:
        super().__init__(message)


class PermisosInsuficientesException(DomainException):
    """El rol del usuario no está autorizado para el recurso (403)."""

    code = "PERMISOS_INSUFICIENTES"
    http_status = 403

    def __init__(self, message: str = MENSAJE_PERMISOS_INSUFICIENTES) -> None:
        super().__init__(message)
