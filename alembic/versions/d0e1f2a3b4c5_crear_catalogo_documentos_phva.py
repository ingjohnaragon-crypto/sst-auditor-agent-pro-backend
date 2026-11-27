"""Crea catálogo PHVA, documentos de empresa y vínculo con estándares 0312.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tipos_documento_sst",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=64), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("fase", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("codigo", name="uq_tipos_documento_sst_codigo"),
    )
    op.create_index("ix_tipos_documento_sst_codigo", "tipos_documento_sst", ["codigo"])
    op.create_index("ix_tipos_documento_sst_fase", "tipos_documento_sst", ["fase"])

    op.create_table(
        "documentos_empresa",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_id", sa.Uuid(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nombre_original", sa.String(length=255), nullable=True),
        sa.Column("tipo_mime", sa.String(length=100), nullable=True),
        sa.Column("tamano_bytes", sa.Integer(), nullable=True),
        sa.Column("clave_objeto", sa.String(length=500), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["tipo_id"], ["tipos_documento_sst.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "tipo_id", name="uq_documentos_empresa_empresa_tipo"),
    )
    op.create_index("ix_documentos_empresa_empresa_id", "documentos_empresa", ["empresa_id"])
    op.create_index("ix_documentos_empresa_tipo_id", "documentos_empresa", ["tipo_id"])

    op.create_table(
        "tipos_documento_estandar",
        sa.Column("tipo_id", sa.Uuid(), nullable=False),
        sa.Column("estandar_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tipo_id"], ["tipos_documento_sst.id"]),
        sa.ForeignKeyConstraint(["estandar_id"], ["estandares_minimos.id"]),
        sa.PrimaryKeyConstraint("tipo_id", "estandar_id", name="pk_tipos_documento_estandar"),
    )


def downgrade() -> None:
    op.drop_table("tipos_documento_estandar")
    op.drop_index("ix_documentos_empresa_tipo_id", table_name="documentos_empresa")
    op.drop_index("ix_documentos_empresa_empresa_id", table_name="documentos_empresa")
    op.drop_table("documentos_empresa")
    op.drop_index("ix_tipos_documento_sst_fase", table_name="tipos_documento_sst")
    op.drop_index("ix_tipos_documento_sst_codigo", table_name="tipos_documento_sst")
    op.drop_table("tipos_documento_sst")
