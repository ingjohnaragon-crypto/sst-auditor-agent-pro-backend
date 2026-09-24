"""Modelo ORM de la tabla `evidencias`."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class EvidenciaORM(Base):
    """Fila de metadatos de un documento de soporte."""

    __tablename__ = "evidencias"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    calificacion_estandar_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("calificaciones_estandar.id"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer(), nullable=False)
    ruta_almacenamiento: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    fecha_eliminacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
