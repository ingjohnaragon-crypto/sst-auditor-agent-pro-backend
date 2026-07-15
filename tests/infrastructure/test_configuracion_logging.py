"""Pruebas de la configuración de logging de la aplicación."""

import logging
from collections.abc import Iterator

import pytest
from src.infrastructure.config.configuracion_logging import (
    FORMATO_LOG,
    configurar_logging,
)


@pytest.fixture(autouse=True)
def _restaurar_logging() -> Iterator[None]:
    # `basicConfig(force=True)` cierra los handlers previos del root logger, así que
    # reinstalarlos sería frágil: solo retiramos los que creó la prueba y dejamos
    # que pytest vuelva a instalar los suyos en la siguiente fase.
    raiz = logging.getLogger()
    nivel_original = raiz.level
    handlers_previos = raiz.handlers[:]
    yield
    for handler in raiz.handlers[:]:
        if handler not in handlers_previos:
            raiz.removeHandler(handler)
            handler.close()
    raiz.setLevel(nivel_original)


def test_should_usar_nivel_info_cuando_log_level_no_definido() -> None:
    configurar_logging()

    assert logging.getLogger().level == logging.INFO


def test_should_aplicar_nivel_debug_cuando_log_level_es_debug() -> None:
    configurar_logging("DEBUG")

    assert logging.getLogger().level == logging.DEBUG


def test_should_normalizar_nivel_en_minusculas() -> None:
    configurar_logging("warning")

    assert logging.getLogger().level == logging.WARNING


def test_should_degradar_a_info_cuando_nivel_es_invalido() -> None:
    configurar_logging("NO_EXISTE")

    assert logging.getLogger().level == logging.INFO


def test_should_configurar_formato_esperado() -> None:
    configurar_logging()

    raiz = logging.getLogger()
    assert len(raiz.handlers) > 0
    formateador = raiz.handlers[0].formatter
    assert formateador is not None
    # Se formatea un registro sintético en lugar de inspeccionar internals
    # (`_fmt`) del módulo `logging`.
    registro = logging.LogRecord(
        name="prueba.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="mensaje de prueba",
        args=None,
        exc_info=None,
    )
    salida = formateador.format(registro)
    assert salida.endswith("INFO prueba.logger mensaje de prueba")
    assert FORMATO_LOG == "%(asctime)s %(levelname)s %(name)s %(message)s"
