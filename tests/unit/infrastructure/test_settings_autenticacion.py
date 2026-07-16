"""Pruebas de las variables de BD y JWT agregadas a `Settings`."""

import pytest
from pydantic import ValidationError
from src.infrastructure.config.settings import Settings

SECRETO_VALIDO = "secreto-de-firma-para-pruebas-de-32-caracteres!!"
URL_PRUEBAS = "sqlite+aiosqlite:///:memory:"


def test_should_cargar_defaults_de_jwt_when_solo_llegan_obligatorias() -> None:
    settings = Settings(_env_file=None, jwt_secreto=SECRETO_VALIDO, url_base_datos=URL_PRUEBAS)

    assert settings.jwt_algoritmo == "HS256"
    assert settings.jwt_minutos_expiracion_acceso == 30
    assert settings.jwt_dias_expiracion_refresco == 7


def test_should_rechazar_jwt_secreto_menor_a_32_caracteres() -> None:
    with pytest.raises(ValidationError, match="32"):
        Settings(_env_file=None, jwt_secreto="secreto-corto", url_base_datos=URL_PRUEBAS)


def test_should_fallar_when_falta_jwt_secreto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRETO", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, url_base_datos=URL_PRUEBAS)


def test_should_fallar_when_falta_url_base_datos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("URL_BASE_DATOS", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secreto=SECRETO_VALIDO)


def test_should_leer_configuracion_jwt_desde_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_MINUTOS_EXPIRACION_ACCESO", "15")
    monkeypatch.setenv("JWT_DIAS_EXPIRACION_REFRESCO", "1")

    settings = Settings(_env_file=None, jwt_secreto=SECRETO_VALIDO, url_base_datos=URL_PRUEBAS)

    assert settings.jwt_minutos_expiracion_acceso == 15
    assert settings.jwt_dias_expiracion_refresco == 1
