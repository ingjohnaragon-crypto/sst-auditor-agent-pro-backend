"""Modelo ORM de la tabla `empresas` — mapeo exclusivo de la infraestructura."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class EmpresaORM(Base):
    """Fila de la tabla `empresas`; el dominio nunca ve esta clase."""

    __tablename__ = "empresas"
    __table_args__ = (UniqueConstraint("nit", name="uq_empresas_nit"),)

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), nullable=False)
    actividad_economica: Mapped[str] = mapped_column(String(200), nullable=False)
    nivel_riesgo_arl: Mapped[str] = mapped_column(String(5), nullable=False)
    numero_trabajadores: Mapped[int] = mapped_column(Integer(), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
