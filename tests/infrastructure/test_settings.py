"""Pruebas de la configuración tipada de la aplicación."""

import pytest
from src.infrastructure.config.settings import Settings, get_settings


def test_should_load_default_values_when_no_env_vars_are_set() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "SST Auditor Agent Pro"
    assert settings.app_version == "0.1.0"
    assert settings.api_prefix == "/api/v1"


def test_should_usar_log_level_info_por_defecto() -> None:
    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"


def test_should_leer_log_level_desde_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"


def test_should_override_values_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_NAME", "Auditor Custom")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("API_PREFIX", "/api/v2")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Auditor Custom"
    assert settings.app_version == "9.9.9"
    assert settings.api_prefix == "/api/v2"


def test_deberia_usar_origen_localhost_4200_por_defecto() -> None:
    settings = Settings(_env_file=None)

    assert settings.origenes_cors == ["http://localhost:4200"]


def test_deberia_leer_origenes_cors_desde_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORIGENES_CORS", '["https://app.example.com"]')

    settings = Settings(_env_file=None)

    assert settings.origenes_cors == ["https://app.example.com"]


def test_should_return_cached_instance_from_get_settings() -> None:
    first = get_settings()
    second = get_settings()

    assert first is second
