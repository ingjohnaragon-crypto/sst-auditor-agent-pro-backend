"""Modelo ORM de la tabla `controles_riesgo`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.infrastructure.database.modelos.evaluacion_riesgo_orm import (
        EvaluacionRiesgoORM,
    )


class ControlRiesgoORM(Base):
    """Fila de `controles_riesgo`; el dominio nunca ve esta clase."""

    __tablename__ = "controles_riesgo"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    evaluacion_riesgo_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("evaluaciones_riesgo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    evaluacion: Mapped[EvaluacionRiesgoORM] = relationship(
        "EvaluacionRiesgoORM", back_populates="controles"
    )
