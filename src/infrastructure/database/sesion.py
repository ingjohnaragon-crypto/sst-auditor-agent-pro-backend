"""Motor async y fábrica de sesiones de SQLAlchemy — creación perezosa y cacheada."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config.settings import get_settings


@lru_cache
def obtener_motor() -> AsyncEngine:
    """Crea (una sola vez) el motor async a partir de `URL_BASE_DATOS`."""
    return create_async_engine(get_settings().url_base_datos)


@lru_cache
def obtener_fabrica_sesiones() -> async_sessionmaker[AsyncSession]:
    """Crea (una sola vez) la fábrica de sesiones async."""
    return async_sessionmaker(obtener_motor(), expire_on_commit=False)


async def obtener_sesion() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: sesión por petición con commit al éxito y rollback al error."""
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        try:
            yield sesion
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise
