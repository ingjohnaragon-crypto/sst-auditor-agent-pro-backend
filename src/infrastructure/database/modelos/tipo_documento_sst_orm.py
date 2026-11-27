"""ORM del catálogo `tipos_documento_sst`."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TipoDocumentoSstORM(Base):
    """Fila del catálogo de documentos obligatorios por fase PHVA."""

    __tablename__ = "tipos_documento_sst"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fase: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
