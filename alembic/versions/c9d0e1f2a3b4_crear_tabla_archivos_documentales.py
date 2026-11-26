"""Crea la tabla de metadatos `archivos_documentales`.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archivos_documentales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("nombre_original", sa.String(length=255), nullable=False),
        sa.Column("tipo_mime", sa.String(length=100), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("clave_objeto", sa.String(length=500), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clave_objeto", name="uq_archivos_documentales_clave_objeto"),
    )
    op.create_index(
        "ix_archivos_documentales_empresa_id",
        "archivos_documentales",
        ["empresa_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_archivos_documentales_empresa_id", table_name="archivos_documentales")
    op.drop_table("archivos_documentales")
