"""DTO de salida con el perfil del usuario autenticado — sin credenciales."""

from uuid import UUID

from pydantic import BaseModel


class RespuestaUsuario(BaseModel):
    """Perfil público del usuario; nunca incluye `hash_contrasena`."""

    id: UUID
    nombre_completo: str
    correo: str
    rol: str
