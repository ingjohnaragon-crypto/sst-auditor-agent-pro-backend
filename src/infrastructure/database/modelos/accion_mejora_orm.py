"""Modelo ORM de la tabla `acciones_mejora`."""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AccionMejoraORM(Base):
    """Fila del borrador. El responsable sugerido puede ir vacío."""

    __tablename__ = "acciones_mejora"
    __table_args__ = (
        UniqueConstraint(
            "plan_mejoramiento_id",
            "estandar_minimo_id",
            name="uq_acciones_mejora_plan_estandar",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    plan_mejoramiento_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("planes_mejoramiento.id"),
        nullable=False,
        index=True,
    )
    estandar_minimo_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("estandares_minimos.id"),
        nullable=False,
    )
    ciclo_phva: Mapped[str] = mapped_column(String(20), nullable=False)
    responsable_sugerido: Mapped[str | None] = mapped_column(String(150), nullable=True)
