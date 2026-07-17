"""Modelo ORM de la tabla `catalogos_referencia` — soporte GTC 45 / enums SST."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CatalogoReferenciaORM(Base):
    """Fila de catálogo de referencia (ND/NE/NC, controles, etc.); no es entidad transaccional."""

    __tablename__ = "catalogos_referencia"
    __table_args__ = (
        UniqueConstraint("tipo", "codigo", name="uq_catalogos_referencia_tipo_codigo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    valor_numerico: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    etiqueta: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    orden: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
