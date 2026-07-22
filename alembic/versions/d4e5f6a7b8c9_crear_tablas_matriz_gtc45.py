"""Crea tablas de matriz GTC 45: procesos, peligros, evaluaciones y controles.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "procesos_actividades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("es_rutinaria", sa.Boolean(), nullable=False),
        sa.Column("zona_lugar", sa.String(length=150), nullable=True),
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
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_procesos_actividades_empresa_id",
        "procesos_actividades",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "peligros",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proceso_actividad_id", sa.Uuid(), nullable=False),
        sa.Column("clasificacion", sa.String(length=40), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("efectos_posibles", sa.Text(), nullable=True),
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
            ["proceso_actividad_id"],
            ["procesos_actividades.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_peligros_proceso_actividad_id",
        "peligros",
        ["proceso_actividad_id"],
        unique=False,
    )

    op.create_table(
        "evaluaciones_riesgo",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("peligro_id", sa.Uuid(), nullable=False),
        sa.Column("nivel_deficiencia", sa.SmallInteger(), nullable=False),
        sa.Column("nivel_exposicion", sa.SmallInteger(), nullable=False),
        sa.Column("nivel_consecuencia", sa.SmallInteger(), nullable=False),
        sa.Column("nivel_probabilidad", sa.SmallInteger(), nullable=False),
        sa.Column("nivel_riesgo", sa.Integer(), nullable=False),
        sa.Column("interpretacion_nr", sa.String(length=5), nullable=False),
        sa.Column("aceptabilidad", sa.String(length=40), nullable=False),
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
        sa.ForeignKeyConstraint(["peligro_id"], ["peligros.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("peligro_id", name="uq_evaluaciones_riesgo_peligro_id"),
    )

    op.create_table(
        "controles_riesgo",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluacion_riesgo_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
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
            ["evaluacion_riesgo_id"],
            ["evaluaciones_riesgo.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_controles_riesgo_evaluacion_riesgo_id",
        "controles_riesgo",
        ["evaluacion_riesgo_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_controles_riesgo_evaluacion_riesgo_id", table_name="controles_riesgo")
    op.drop_table("controles_riesgo")
    op.drop_table("evaluaciones_riesgo")
    op.drop_index("ix_peligros_proceso_actividad_id", table_name="peligros")
    op.drop_table("peligros")
    op.drop_index("ix_procesos_actividades_empresa_id", table_name="procesos_actividades")
    op.drop_table("procesos_actividades")
