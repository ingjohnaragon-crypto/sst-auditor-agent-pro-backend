"""Crea la tabla de auditoría `accesos_evidencia`.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accesos_evidencia",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidencia_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("resultado", sa.String(length=32), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evidencia_id"], ["evidencias.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accesos_evidencia_evidencia_id",
        "accesos_evidencia",
        ["evidencia_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_accesos_evidencia_evidencia_id", table_name="accesos_evidencia")
    op.drop_table("accesos_evidencia")
