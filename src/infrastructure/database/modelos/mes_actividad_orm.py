"""Modelo ORM de la tabla `meses_actividad`."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class MesActividadORM(Base):
    """Mes (1 a 12) en el que corre una actividad del cronograma."""

    __tablename__ = "meses_actividad"
    __table_args__ = (CheckConstraint("mes >= 1 AND mes <= 12", name="ck_meses_actividad_mes"),)

    actividad_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("actividades_cronograma.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mes: Mapped[int] = mapped_column(SmallInteger(), primary_key=True)
