"""Modelo ORM de la tabla `evaluaciones_riesgo`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.infrastructure.database.modelos.control_riesgo_orm import ControlRiesgoORM
    from src.infrastructure.database.modelos.peligro_orm import PeligroORM


class EvaluacionRiesgoORM(Base):
    """Fila de `evaluaciones_riesgo`; el dominio nunca ve esta clase."""

    __tablename__ = "evaluaciones_riesgo"
    __table_args__ = (UniqueConstraint("peligro_id", name="uq_evaluaciones_riesgo_peligro_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    peligro_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("peligros.id", ondelete="CASCADE"), nullable=False
    )
    nivel_deficiencia: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    nivel_exposicion: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    nivel_consecuencia: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    nivel_probabilidad: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    nivel_riesgo: Mapped[int] = mapped_column(Integer(), nullable=False)
    interpretacion_nr: Mapped[str] = mapped_column(String(5), nullable=False)
    aceptabilidad: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    peligro: Mapped[PeligroORM] = relationship("PeligroORM", back_populates="evaluacion")
    controles: Mapped[list[ControlRiesgoORM]] = relationship(
        "ControlRiesgoORM",
        back_populates="evaluacion",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
