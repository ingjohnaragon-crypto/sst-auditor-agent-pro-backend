"""DTO de entrada del inicio de sesión."""

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

LONGITUD_MINIMA_CONTRASENA = 8


class SolicitudLogin(BaseModel):
    """Credenciales de inicio de sesión; la contraseña nunca aparece en repr ni logs."""

    correo: EmailStr
    contrasena: SecretStr = Field(min_length=LONGITUD_MINIMA_CONTRASENA)

    @field_validator("correo", mode="after")
    @classmethod
    def normalizar_correo(cls, valor: str) -> str:
        """Normaliza el correo a minúsculas antes de consultar la base de datos."""
        return valor.lower()
