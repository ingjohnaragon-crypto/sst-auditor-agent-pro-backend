"""Entorno de Alembic en modo async — la URL de conexión proviene de Settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine
from src.infrastructure.config.settings import Settings
from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos import UsuarioORM  # noqa: F401 — registra la tabla

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def obtener_url() -> str:
    """Resuelve la URL de la base de datos desde el entorno (sin cache, apto para tests)."""
    return Settings().url_base_datos


def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo offline (genera SQL sin conexión)."""
    context.configure(
        url=obtener_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones(conexion: Connection) -> None:
    """Configura el contexto sobre una conexión síncrona y ejecuta las migraciones."""
    context.configure(connection=conexion, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Ejecuta las migraciones con un motor async creado desde Settings."""
    motor = create_async_engine(obtener_url(), poolclass=pool.NullPool)
    async with motor.connect() as conexion:
        await conexion.run_sync(ejecutar_migraciones)
        await conexion.commit()
    await motor.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
