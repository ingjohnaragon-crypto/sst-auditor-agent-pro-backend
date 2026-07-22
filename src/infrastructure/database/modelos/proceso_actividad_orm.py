"""Modelo ORM de la tabla `procesos_actividades`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.infrastructure.database.modelos.peligro_orm import PeligroORM


class ProcesoActividadORM(Base):
    """Fila de `procesos_actividades`; el dominio nunca ve esta clase."""

    __tablename__ = "procesos_actividades"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    es_rutinaria: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    zona_lugar: Mapped[str | None] = mapped_column(String(150), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    peligros: Mapped[list[PeligroORM]] = relationship(
        "PeligroORM",
        back_populates="proceso",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
