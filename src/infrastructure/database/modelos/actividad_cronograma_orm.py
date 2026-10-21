"""Modelo ORM de la tabla `actividades_cronograma`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.infrastructure.database.modelos.mes_actividad_orm import MesActividadORM


class ActividadCronogramaORM(Base):
    """Fila de `actividades_cronograma`. El responsable es texto, no un usuario."""

    __tablename__ = "actividades_cronograma"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    plan_mejoramiento_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("planes_mejoramiento.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    responsable: Mapped[str] = mapped_column(String(150), nullable=False)
    indicador: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    meses: Mapped[list[MesActividadORM]] = relationship(
        "MesActividadORM",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
