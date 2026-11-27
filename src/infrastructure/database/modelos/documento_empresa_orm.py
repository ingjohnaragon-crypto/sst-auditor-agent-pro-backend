"""ORM de `documentos_empresa` — un vigente por empresa y tipo."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class DocumentoEmpresaORM(Base):
    """Metadatos del documento cargado; el binario vive en R2."""

    __tablename__ = "documentos_empresa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "tipo_id", name="uq_documentos_empresa_empresa_tipo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("empresas.id"), nullable=False, index=True
    )
    tipo_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("tipos_documento_sst.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_carga: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nombre_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamano_bytes: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    clave_objeto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    usuario_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("usuarios.id"), nullable=True
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
