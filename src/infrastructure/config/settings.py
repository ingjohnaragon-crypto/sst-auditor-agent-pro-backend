"""Configuración tipada de la aplicación vía Pydantic Settings."""

from functools import lru_cache

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LONGITUD_MINIMA_JWT_SECRETO = 32
ALGORITMO_JWT_PERMITIDO = "HS256"


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

    # Pool de conexión a la base de datos — defaults conservadores para una instancia.
    bd_pool_tamano: int = 5
    bd_pool_max_extra: int = 10
    bd_pool_pre_ping: bool = True
    bd_pool_reciclar_segundos: int = 1800
    bd_echo_sql: bool = False

    # JWT — el secreto es obligatorio y solo llega por entorno; nunca se versiona.
    jwt_secreto: str
    jwt_algoritmo: str = ALGORITMO_JWT_PERMITIDO
    jwt_minutos_expiracion_acceso: int = 30
    jwt_dias_expiracion_refresco: int = 7

    @field_validator("bd_pool_tamano", "bd_pool_reciclar_segundos")
    @classmethod
    def validar_pool_positivo(cls, valor: int, info: ValidationInfo) -> int:
        """Exige valores estrictamente positivos para el pool (fail-fast al arranque)."""
        if valor < 1:
            variable = (info.field_name or "").upper()
            raise ValueError(f"{variable} debe ser un entero positivo (recibido: {valor})")
        return valor

    @field_validator("bd_pool_max_extra")
    @classmethod
    def validar_pool_no_negativo(cls, valor: int) -> int:
        """El desborde máximo del pool admite cero, pero nunca valores negativos."""
        if valor < 0:
            raise ValueError(f"BD_POOL_MAX_EXTRA no puede ser negativo (recibido: {valor})")
        return valor

    @field_validator("jwt_secreto")
    @classmethod
    def validar_longitud_jwt_secreto(cls, valor: str) -> str:
        """Exige un secreto de firma con entropía mínima razonable (≥ 32 caracteres)."""
        if len(valor) < LONGITUD_MINIMA_JWT_SECRETO:
            raise ValueError(
                f"JWT_SECRETO debe tener al menos {LONGITUD_MINIMA_JWT_SECRETO} caracteres"
            )
        return valor

    @field_validator("jwt_algoritmo")
    @classmethod
    def validar_algoritmo_jwt(cls, valor: str) -> str:
        """Solo HS256 está soportado (alineado con TokensJWT.encode/decode)."""
        if valor != ALGORITMO_JWT_PERMITIDO:
            raise ValueError(
                f"JWT_ALGORITMO debe ser '{ALGORITMO_JWT_PERMITIDO}' (recibido: '{valor}')"
            )
        return valor


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de `Settings` para inyección de dependencias."""
    return Settings()  # type: ignore[call-arg]
