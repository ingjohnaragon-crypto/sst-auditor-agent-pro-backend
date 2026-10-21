"""Crea tablas del plan de mejora y el cronograma.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "planes_mejoramiento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("autoevaluacion_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["autoevaluacion_id"], ["autoevaluaciones.id"]),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "autoevaluacion_id",
            name="uq_planes_mejoramiento_autoevaluacion_id",
        ),
    )
    op.create_index(
        "ix_planes_mejoramiento_empresa_id",
        "planes_mejoramiento",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "actividades_cronograma",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_mejoramiento_id", sa.Uuid(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("responsable", sa.String(length=150), nullable=False),
        sa.Column("indicador", sa.String(length=200), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["plan_mejoramiento_id"],
            ["planes_mejoramiento.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_actividades_cronograma_plan_id",
        "actividades_cronograma",
        ["plan_mejoramiento_id"],
        unique=False,
    )

    op.create_table(
        "meses_actividad",
        sa.Column("actividad_id", sa.Uuid(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("mes >= 1 AND mes <= 12", name="ck_meses_actividad_mes"),
        sa.ForeignKeyConstraint(
            ["actividad_id"],
            ["actividades_cronograma.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("actividad_id", "mes"),
    )


def downgrade() -> None:
    op.drop_table("meses_actividad")
    op.drop_index("ix_actividades_cronograma_plan_id", table_name="actividades_cronograma")
    op.drop_table("actividades_cronograma")
    op.drop_index("ix_planes_mejoramiento_empresa_id", table_name="planes_mejoramiento")
    op.drop_table("planes_mejoramiento")
