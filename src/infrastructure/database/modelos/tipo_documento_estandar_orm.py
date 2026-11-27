"""ORM de unión tipo de documento ↔ estándar mínimo 0312."""

from uuid import UUID

from sqlalchemy import ForeignKey, PrimaryKeyConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TipoDocumentoEstandarORM(Base):
    """Vínculo de catálogo; no copia el objeto R2."""

    __tablename__ = "tipos_documento_estandar"
    __table_args__ = (
        PrimaryKeyConstraint("tipo_id", "estandar_id", name="pk_tipos_documento_estandar"),
    )

    tipo_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("tipos_documento_sst.id"), nullable=False
    )
    estandar_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("estandares_minimos.id"), nullable=False
    )
