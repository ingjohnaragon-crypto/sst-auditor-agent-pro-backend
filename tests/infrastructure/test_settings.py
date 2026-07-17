"""Pruebas de la configuración tipada de la aplicación."""

import pytest
from pydantic import ValidationError
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


def test_should_usar_defaults_de_pool_when_no_hay_variables_de_entorno() -> None:
    """Sin variables BD_* el pool queda con los defaults conservadores."""
    settings = Settings(_env_file=None)

    assert settings.bd_pool_tamano == 5
    assert settings.bd_pool_max_extra == 10
    assert settings.bd_pool_pre_ping is True
    assert settings.bd_pool_reciclar_segundos == 1800
    assert settings.bd_echo_sql is False


def test_should_leer_configuracion_de_pool_when_variables_definidas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Las variables BD_* del entorno sobreescriben los defaults del pool."""
    monkeypatch.setenv("BD_POOL_TAMANO", "20")
    monkeypatch.setenv("BD_POOL_MAX_EXTRA", "5")
    monkeypatch.setenv("BD_POOL_PRE_PING", "false")
    monkeypatch.setenv("BD_POOL_RECICLAR_SEGUNDOS", "900")
    monkeypatch.setenv("BD_ECHO_SQL", "true")

    settings = Settings(_env_file=None)

    assert settings.bd_pool_tamano == 20
    assert settings.bd_pool_max_extra == 5
    assert settings.bd_pool_pre_ping is False
    assert settings.bd_pool_reciclar_segundos == 900
    assert settings.bd_echo_sql is True


@pytest.mark.parametrize("valor", ["0", "-1"])
def test_should_fallar_when_bd_pool_tamano_no_es_positivo(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    """Un tamaño de pool no positivo impide el arranque (fail-fast)."""
    monkeypatch.setenv("BD_POOL_TAMANO", valor)

    with pytest.raises(ValidationError, match="BD_POOL_TAMANO"):
        Settings(_env_file=None)


@pytest.mark.parametrize("valor", ["0", "-1"])
def test_should_fallar_when_bd_pool_reciclar_segundos_no_es_positivo(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    """Un tiempo de reciclaje no positivo impide el arranque (fail-fast)."""
    monkeypatch.setenv("BD_POOL_RECICLAR_SEGUNDOS", valor)

    with pytest.raises(ValidationError, match="BD_POOL_RECICLAR_SEGUNDOS"):
        Settings(_env_file=None)


def test_should_fallar_when_bd_pool_max_extra_es_negativo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un desborde máximo negativo impide el arranque; cero sí es válido."""
    monkeypatch.setenv("BD_POOL_MAX_EXTRA", "-1")

    with pytest.raises(ValidationError, match="BD_POOL_MAX_EXTRA"):
        Settings(_env_file=None)


def test_should_aceptar_bd_pool_max_extra_cero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cero conexiones extra es una configuración válida del pool."""
    monkeypatch.setenv("BD_POOL_MAX_EXTRA", "0")

    settings = Settings(_env_file=None)

    assert settings.bd_pool_max_extra == 0
