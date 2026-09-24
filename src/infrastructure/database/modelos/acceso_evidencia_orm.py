"""Modelo ORM de la tabla `accesos_evidencia`."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AccesoEvidenciaORM(Base):
    """Fila de auditoría de un canje de descarga."""

    __tablename__ = "accesos_evidencia"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    evidencia_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("evidencias.id"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    resultado: Mapped[str] = mapped_column(String(32), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
