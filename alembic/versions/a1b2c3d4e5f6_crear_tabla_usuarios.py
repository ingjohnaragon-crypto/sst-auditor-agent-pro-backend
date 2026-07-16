"""Crea la tabla `usuarios` con índice único en `correo`.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores de la revisión, usados por Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre_completo", sa.String(length=150), nullable=False),
        sa.Column("correo", sa.String(length=254), nullable=False),
        sa.Column("hash_contrasena", sa.String(length=72), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    op.create_index(op.f("ix_usuarios_correo"), "usuarios", ["correo"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_usuarios_correo"), table_name="usuarios")
    op.drop_table("usuarios")
