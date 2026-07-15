"""Configuración tipada de la aplicación vía Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno tipadas de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SST Auditor Agent Pro"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    # Vía entorno se sobreescribe con un JSON array: ORIGENES_CORS='["http://localhost:4200"]'
    origenes_cors: list[str] = ["http://localhost:4200"]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de `Settings` para inyección de dependencias."""
    return Settings()
