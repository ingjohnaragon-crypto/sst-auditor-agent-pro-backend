"""Modelo ORM de la tabla `usuarios` — mapeo exclusivo de la infraestructura."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class UsuarioORM(Base):
    """Fila de la tabla `usuarios`; el dominio nunca ve esta clase."""

    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    hash_contrasena: Mapped[str] = mapped_column(String(72), nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
