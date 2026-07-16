"""Modelos ORM de la infraestructura — nunca se importan desde dominio o aplicación."""

from src.infrastructure.database.modelos.usuario_orm import UsuarioORM

__all__ = ["UsuarioORM"]
