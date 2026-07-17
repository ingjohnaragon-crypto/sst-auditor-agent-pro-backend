"""Modelo ORM de la tabla `estandares_minimos` — catálogo Res. 312 de 2019."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class EstandarMinimoORM(Base):
    """Fila del catálogo de estándares mínimos; el dominio no importa esta clase."""

    __tablename__ = "estandares_minimos"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    ciclo_phva: Mapped[str] = mapped_column(String(20), nullable=False)
    numeral: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    valor_porcentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
