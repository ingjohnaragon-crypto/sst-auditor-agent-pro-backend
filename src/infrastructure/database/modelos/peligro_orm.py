"""Modelo ORM de la tabla `peligros`."""

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
    from src.infrastructure.database.modelos.proceso_actividad_orm import (
        ProcesoActividadORM,
    )


class PeligroORM(Base):
    """Fila de `peligros`; el dominio nunca ve esta clase."""

    __tablename__ = "peligros"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    proceso_actividad_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("procesos_actividades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clasificacion: Mapped[str] = mapped_column(String(40), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    efectos_posibles: Mapped[str | None] = mapped_column(Text(), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    proceso: Mapped[ProcesoActividadORM] = relationship(
        "ProcesoActividadORM", back_populates="peligros"
    )
    evaluacion: Mapped[EvaluacionRiesgoORM | None] = relationship(
        "EvaluacionRiesgoORM",
        back_populates="peligro",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
