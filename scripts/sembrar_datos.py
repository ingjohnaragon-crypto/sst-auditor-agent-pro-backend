"""Orquestador local de seeds SST (catálogos Res. 312 + GTC 45).

Uso:
    poetry run python -m scripts.sembrar_datos

Orden: estándares mínimos → catálogos GTC 45.
Opcional: si existen ADMIN_INICIAL_*, también crea el admin (no falla si faltan).

No se ejecuta al importar ni en el lifespan de FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from src.infrastructure.database.sesion import obtener_fabrica_sesiones

from scripts.crear_usuario_admin import crear_usuario_admin
from scripts.sembrar_catalogos_gtc45 import sembrar_catalogos_gtc45
from scripts.sembrar_estandares_minimos import sembrar_estandares_minimos

logger = logging.getLogger(__name__)

VARIABLES_ADMIN = (
    "ADMIN_INICIAL_CORREO",
    "ADMIN_INICIAL_CONTRASENA",
    "ADMIN_INICIAL_NOMBRE",
)


def hay_credenciales_admin() -> bool:
    """True si están definidas las tres variables del seed de administrador."""
    return all(os.environ.get(nombre) for nombre in VARIABLES_ADMIN)


async def sembrar_datos() -> None:
    """Ejecuta los seeds de catálogos (y admin opcional) en una sesión."""
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        try:
            creados_e, omitidos_e = await sembrar_estandares_minimos(sesion)
            logger.info(
                "Estándares: creados=%s omitidos=%s",
                creados_e,
                omitidos_e,
            )
            creados_c, omitidos_c = await sembrar_catalogos_gtc45(sesion)
            logger.info(
                "Catálogos GTC 45: creados=%s omitidos=%s",
                creados_c,
                omitidos_c,
            )
            if hay_credenciales_admin():
                creado_admin = await crear_usuario_admin(sesion)
                logger.info(
                    "Administrador: %s",
                    "creado" if creado_admin else "ya existía / omitido",
                )
            else:
                logger.info("ADMIN_INICIAL_* no definidas; se omite el seed de administrador")
            await sesion.commit()
        except Exception as exc:
            await sesion.rollback()
            raise RuntimeError(
                f"Falló el orquestador sembrar_datos: {exc}. "
                "¿Ejecutaste `poetry run alembic upgrade head`?"
            ) from exc


async def principal() -> None:
    """Punto de entrada del orquestador."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    await sembrar_datos()
    logger.info("Orquestador sembrar_datos finalizado")


if __name__ == "__main__":
    asyncio.run(principal())
