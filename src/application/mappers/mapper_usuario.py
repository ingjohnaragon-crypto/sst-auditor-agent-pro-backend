"""Transformación de la entidad `Usuario` a sus DTOs de respuesta."""

from src.application.dto.respuesta_usuario import RespuestaUsuario
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.models.usuario import Usuario


class MapperUsuario:
    """Mapper estático dominio → DTO."""

    @staticmethod
    def a_respuesta(usuario: Usuario) -> RespuestaUsuario:
        """Convierte la entidad a su DTO público (excluye el hash de la contraseña)."""
        if usuario.id is None:
            # Un usuario autenticado siempre proviene de la base de datos con id asignado.
            raise TokenInvalidoException()
        return RespuestaUsuario(
            id=usuario.id,
            nombre_completo=usuario.nombre_completo,
            correo=usuario.correo,
            rol=usuario.rol.value,
        )
