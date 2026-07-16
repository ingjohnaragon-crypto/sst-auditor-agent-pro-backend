"""Implementación SQLAlchemy del puerto `RepositorioUsuario`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.usuario import RolUsuario, Usuario
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.infrastructure.database.modelos.usuario_orm import UsuarioORM


class RepositorioUsuarioSQLAlchemy(RepositorioUsuario):
    """Persistencia de `Usuario` sobre la tabla `usuarios` — devuelve dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def buscar_por_correo(self, correo: str) -> Usuario | None:
        consulta = select(UsuarioORM).where(UsuarioORM.correo == correo.lower())
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    async def buscar_por_id(self, id: UUID) -> Usuario | None:
        fila = await self._sesion.get(UsuarioORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def guardar(self, usuario: Usuario) -> Usuario:
        fila = self._a_orm(usuario)
        fila = await self._sesion.merge(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def existe_por_correo(self, correo: str) -> bool:
        consulta = select(UsuarioORM.id).where(UsuarioORM.correo == correo.lower())
        return (await self._sesion.execute(consulta)).scalar_one_or_none() is not None

    @staticmethod
    def _a_dominio(fila: UsuarioORM) -> Usuario:
        return Usuario(
            id=fila.id,
            nombre_completo=fila.nombre_completo,
            correo=fila.correo,
            hash_contrasena=fila.hash_contrasena,
            rol=RolUsuario(fila.rol),
            activo=fila.activo,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(usuario: Usuario) -> UsuarioORM:
        return UsuarioORM(
            id=usuario.id if usuario.id is not None else uuid4(),
            nombre_completo=usuario.nombre_completo,
            correo=usuario.correo,
            hash_contrasena=usuario.hash_contrasena,
            rol=usuario.rol.value,
            activo=usuario.activo,
        )
