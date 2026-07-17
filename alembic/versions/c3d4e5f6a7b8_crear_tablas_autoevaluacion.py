"""Crea tablas de autoevaluación: empresas, autoevaluaciones y calificaciones.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("nit", sa.String(length=20), nullable=False),
        sa.Column("actividad_economica", sa.String(length=200), nullable=False),
        sa.Column("nivel_riesgo_arl", sa.String(length=5), nullable=False),
        sa.Column("numero_trabajadores", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint("nit", name="uq_empresas_nit"),
    )

    op.create_table(
        "autoevaluaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("puntaje_total", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "requiere_plan_mejora",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
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
    )
    op.create_index(
        "ix_autoevaluaciones_empresa_id",
        "autoevaluaciones",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "calificaciones_estandar",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("autoevaluacion_id", sa.Uuid(), nullable=False),
        sa.Column("estandar_id", sa.Uuid(), nullable=False),
        sa.Column("resultado", sa.String(length=20), nullable=False),
        sa.Column("puntaje", sa.Numeric(5, 2), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["estandar_id"], ["estandares_minimos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "autoevaluacion_id",
            "estandar_id",
            name="uq_calificaciones_estandar_autoevaluacion_estandar",
        ),
    )
    op.create_index(
        "ix_calificaciones_estandar_autoevaluacion_id",
        "calificaciones_estandar",
        ["autoevaluacion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_calificaciones_estandar_autoevaluacion_id",
        table_name="calificaciones_estandar",
    )
    op.drop_table("calificaciones_estandar")
    op.drop_index("ix_autoevaluaciones_empresa_id", table_name="autoevaluaciones")
    op.drop_table("autoevaluaciones")
    op.drop_table("empresas")
