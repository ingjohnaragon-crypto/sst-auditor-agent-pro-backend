"""Crea las tablas de catálogos SST: `estandares_minimos` y `catalogos_referencia`.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estandares_minimos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ciclo_phva", sa.String(length=20), nullable=False),
        sa.Column("numeral", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("valor_porcentual", sa.Numeric(5, 2), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_estandares_minimos_numeral"),
        "estandares_minimos",
        ["numeral"],
        unique=True,
    )

    op.create_table(
        "catalogos_referencia",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("valor_numerico", sa.Integer(), nullable=True),
        sa.Column("etiqueta", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tipo", "codigo", name="uq_catalogos_referencia_tipo_codigo"),
    )


def downgrade() -> None:
    op.drop_table("catalogos_referencia")
    op.drop_index(op.f("ix_estandares_minimos_numeral"), table_name="estandares_minimos")
    op.drop_table("estandares_minimos")
