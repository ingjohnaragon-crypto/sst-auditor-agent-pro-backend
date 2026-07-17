"""Modelo ORM de la tabla `calificaciones_estandar` — ítems de una autoevaluación."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CalificacionEstandarORM(Base):
    """Fila de calificación de un estándar dentro de una autoevaluación."""

    __tablename__ = "calificaciones_estandar"
    __table_args__ = (
        UniqueConstraint(
            "autoevaluacion_id",
            "estandar_id",
            name="uq_calificaciones_estandar_autoevaluacion_estandar",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    autoevaluacion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("autoevaluaciones.id"),
        nullable=False,
        index=True,
    )
    estandar_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("estandares_minimos.id"),
        nullable=False,
    )
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    puntaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text(), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
