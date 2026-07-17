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


def _argumentos_motor() -> dict[str, object]:
    """Kwargs del motor desde `Settings`; el dimensionamiento solo aplica fuera de SQLite."""
    settings = get_settings()
    argumentos: dict[str, object] = {
        "echo": settings.bd_echo_sql,
        "pool_pre_ping": settings.bd_pool_pre_ping,
        "pool_recycle": settings.bd_pool_reciclar_segundos,
    }
    # SQLite (tests) usa StaticPool, que no acepta pool_size ni max_overflow.
    if not settings.url_base_datos.startswith("sqlite"):
        argumentos["pool_size"] = settings.bd_pool_tamano
        argumentos["max_overflow"] = settings.bd_pool_max_extra
    return argumentos


@lru_cache
def obtener_motor() -> AsyncEngine:
    """Crea (una sola vez) el motor async a partir de `URL_BASE_DATOS`."""
    return create_async_engine(get_settings().url_base_datos, **_argumentos_motor())


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
