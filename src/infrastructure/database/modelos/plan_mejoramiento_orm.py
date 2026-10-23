"""Modelo ORM de la tabla `planes_mejoramiento`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.infrastructure.database.modelos.actividad_cronograma_orm import (
    ActividadCronogramaORM,
)


class PlanMejoramientoORM(Base):
    """Fila de `planes_mejoramiento`. Una autoevaluación admite como máximo un plan."""

    __tablename__ = "planes_mejoramiento"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("empresas.id"),
        nullable=False,
        index=True,
    )
    autoevaluacion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("autoevaluaciones.id"),
        nullable=False,
        unique=True,
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

    actividades: Mapped[list[ActividadCronogramaORM]] = relationship(
        "ActividadCronogramaORM",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by=(ActividadCronogramaORM.fecha_creacion, ActividadCronogramaORM.id),
    )
