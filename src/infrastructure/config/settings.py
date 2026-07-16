"""Configuración tipada de la aplicación vía Pydantic Settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LONGITUD_MINIMA_JWT_SECRETO = 32


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

    # Persistencia — sin default: la URL real solo llega por entorno (fail-fast).
    url_base_datos: str

    # JWT — el secreto es obligatorio y solo llega por entorno; nunca se versiona.
    jwt_secreto: str
    jwt_algoritmo: str = "HS256"
    jwt_minutos_expiracion_acceso: int = 30
    jwt_dias_expiracion_refresco: int = 7

    @field_validator("jwt_secreto")
    @classmethod
    def validar_longitud_jwt_secreto(cls, valor: str) -> str:
        """Exige un secreto de firma con entropía mínima razonable (≥ 32 caracteres)."""
        if len(valor) < LONGITUD_MINIMA_JWT_SECRETO:
            raise ValueError(
                f"JWT_SECRETO debe tener al menos {LONGITUD_MINIMA_JWT_SECRETO} caracteres"
            )
        return valor


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de `Settings` para inyección de dependencias."""
    return Settings()  # type: ignore[call-arg]
