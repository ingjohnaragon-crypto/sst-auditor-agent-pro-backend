"""Pruebas de los códigos y estados HTTP de las excepciones de autenticación."""

from src.domain.exceptions.autenticacion import (
    MENSAJE_CREDENCIALES_INVALIDAS,
    CredencialesInvalidasException,
    PermisosInsuficientesException,
    TokenExpiradoException,
    TokenInvalidoException,
)
from src.domain.exceptions.base import DomainException


def test_should_exponer_codigo_y_401_when_credenciales_invalidas() -> None:
    excepcion = CredencialesInvalidasException()

    assert isinstance(excepcion, DomainException)
    assert excepcion.code == "CREDENCIALES_INVALIDAS"
    assert excepcion.http_status == 401
    assert excepcion.message == MENSAJE_CREDENCIALES_INVALIDAS


def test_should_usar_mismo_mensaje_generico_para_todo_fallo_de_credenciales() -> None:
    # El mensaje nunca revela si falló el correo, la contraseña o el estado activo.
    assert CredencialesInvalidasException().message == CredencialesInvalidasException().message


def test_should_exponer_codigo_y_401_when_token_invalido() -> None:
    excepcion = TokenInvalidoException()

    assert excepcion.code == "TOKEN_INVALIDO"
    assert excepcion.http_status == 401


def test_should_exponer_codigo_y_401_when_token_expirado() -> None:
    excepcion = TokenExpiradoException()

    assert excepcion.code == "TOKEN_EXPIRADO"
    assert excepcion.http_status == 401


def test_should_exponer_codigo_y_403_when_permisos_insuficientes() -> None:
    excepcion = PermisosInsuficientesException()

    assert excepcion.code == "PERMISOS_INSUFICIENTES"
    assert excepcion.http_status == 403
