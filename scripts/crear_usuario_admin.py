"""Seed idempotente del administrador inicial — credenciales solo desde el entorno.

Uso:
    py -m scripts.crear_usuario_admin

Variables de entorno requeridas:
    ADMIN_INICIAL_CORREO, ADMIN_INICIAL_CONTRASENA, ADMIN_INICIAL_NOMBRE
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.database.sesion import obtener_fabrica_sesiones
from src.infrastructure.repositories.repositorio_usuario_sqlalchemy import (
    RepositorioUsuarioSQLAlchemy,
)
from src.infrastructure.security.hash_bcrypt import HashBcrypt

logger = logging.getLogger(__name__)

VARIABLES_REQUERIDAS = (
    "ADMIN_INICIAL_CORREO",
    "ADMIN_INICIAL_CONTRASENA",
    "ADMIN_INICIAL_NOMBRE",
)


def leer_credenciales_del_entorno() -> tuple[str, str, str]:
    """Lee las credenciales del seed del entorno; falla con mensaje claro si faltan."""
    faltantes = [nombre for nombre in VARIABLES_REQUERIDAS if not os.environ.get(nombre)]
    if faltantes:
        raise RuntimeError(
            f"Faltan variables de entorno requeridas para el seed: {', '.join(faltantes)}"
        )
    return (
        os.environ["ADMIN_INICIAL_CORREO"],
        os.environ["ADMIN_INICIAL_CONTRASENA"],
        os.environ["ADMIN_INICIAL_NOMBRE"],
    )


async def crear_usuario_admin(sesion: AsyncSession) -> bool:
    """Crea el administrador inicial si no existe. Devuelve True si lo creó."""
    correo, contrasena, nombre = leer_credenciales_del_entorno()
    repositorio = RepositorioUsuarioSQLAlchemy(sesion)
    if await repositorio.existe_por_correo(correo.lower()):
        logger.info("El usuario administrador %s ya existe; no se duplica", correo.lower())
        return False
    hash_contrasena = await HashBcrypt().generar_hash(contrasena)
    usuario = Usuario.crear(
        nombre_completo=nombre,
        correo=correo,
        hash_contrasena=hash_contrasena,
        rol=RolUsuario.ADMINISTRADOR,
    )
    await repositorio.guardar(usuario)
    logger.info("Usuario administrador %s creado correctamente", usuario.correo)
    return True


async def principal() -> None:
    """Punto de entrada async: abre sesión, ejecuta el seed y confirma la transacción."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        await crear_usuario_admin(sesion)
        await sesion.commit()


if __name__ == "__main__":
    asyncio.run(principal())
