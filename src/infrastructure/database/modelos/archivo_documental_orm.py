"""Modelo ORM de la tabla `archivos_documentales`."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ArchivoDocumentalORM(Base):
    """Fila de metadatos de un documento de empresa (binario en R2)."""

    __tablename__ = "archivos_documentales"
    __table_args__ = (
        UniqueConstraint("clave_objeto", name="uq_archivos_documentales_clave_objeto"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("empresas.id"),
        nullable=False,
        index=True,
    )
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer(), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    clave_objeto: Mapped[str] = mapped_column(String(500), nullable=False)
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    fecha_carga: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
