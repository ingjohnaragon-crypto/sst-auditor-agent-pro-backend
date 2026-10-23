"""Crea la tabla del borrador de acciones de mejora.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acciones_mejora",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_mejoramiento_id", sa.Uuid(), nullable=False),
        sa.Column("estandar_minimo_id", sa.Uuid(), nullable=False),
        sa.Column("ciclo_phva", sa.String(length=20), nullable=False),
        sa.Column("responsable_sugerido", sa.String(length=150), nullable=True),
        sa.ForeignKeyConstraint(
            ["estandar_minimo_id"],
            ["estandares_minimos.id"],
        ),
        sa.ForeignKeyConstraint(
            ["plan_mejoramiento_id"],
            ["planes_mejoramiento.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_mejoramiento_id",
            "estandar_minimo_id",
            name="uq_acciones_mejora_plan_estandar",
        ),
    )
    op.create_index(
        "ix_acciones_mejora_plan_id",
        "acciones_mejora",
        ["plan_mejoramiento_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_acciones_mejora_plan_id", table_name="acciones_mejora")
    op.drop_table("acciones_mejora")
