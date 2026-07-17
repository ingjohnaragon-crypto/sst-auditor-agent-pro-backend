"""Modelo ORM de la tabla `autoevaluaciones` — agregado raíz de la evaluación 0312."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.calificacion_estandar_orm import (
    CalificacionEstandarORM,
)


class AutoevaluacionORM(Base):
    """Fila de la tabla `autoevaluaciones` con calificaciones embebidas."""

    __tablename__ = "autoevaluaciones"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("empresas.id"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date(), nullable=False)
    puntaje_total: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    requiere_plan_mejora: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
        default=False,
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

    calificaciones: Mapped[list[CalificacionEstandarORM]] = relationship(
        "CalificacionEstandarORM",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
