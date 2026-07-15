"""Configuración del logging estándar de la aplicación."""

import logging

FORMATO_LOG = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura el root logger con el nivel indicado y el formato estándar.

    Un nivel inválido degrada a `INFO` sin lanzar excepción, para que un error
    de configuración nunca impida el arranque de la aplicación.
    """
    nivel_numerico = logging.getLevelName(nivel.upper())
    if not isinstance(nivel_numerico, int):
        nivel_numerico = logging.INFO
    logging.basicConfig(level=nivel_numerico, format=FORMATO_LOG, force=True)
