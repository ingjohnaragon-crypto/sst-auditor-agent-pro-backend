"""Seed idempotente del catálogo de tipos documentales PHVA.

Uso:
    poetry run python -m scripts.sembrar_tipos_documento_sst

Fixture: scripts/datos/tipos_documento_sst_phva.json
Override: SEED_FIXTURE_TIPOS_DOCUMENTO=/ruta/alternativa.json

Tras sembrar tipos, vincula opcionalmente códigos → numerales 0312
(si el estándar existe; no falla si falta).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM
from src.infrastructure.database.modelos.tipo_documento_estandar_orm import (
    TipoDocumentoEstandarORM,
)
from src.infrastructure.database.modelos.tipo_documento_sst_orm import TipoDocumentoSstORM
from src.infrastructure.database.sesion import obtener_fabrica_sesiones

logger = logging.getLogger(__name__)

FIXTURE_POR_DEFECTO = Path(__file__).resolve().parent / "datos" / "tipos_documento_sst_phva.json"

# Vínculos sugeridos (SP-268): codigo tipo → numerales Res. 312 (si existen).
VINCULOS_TIPO_NUMERAL: dict[str, tuple[str, ...]] = {
    "POLITICA_SST": ("1.1.1",),
    "MATRIZ_RIESGOS_GTC45": ("2.1.1",),
    "PLAN_TRABAJO_ANUAL": ("1.1.6",),
    "PROGRAMA_CAPACITACION": ("1.2.1",),
    "REGISTRO_EPP": ("2.2.1",),
    "ACTAS_COPASST": ("1.1.7",),
    "FURAT": ("2.3.1",),
    "INDICADORES_GESTION": ("3.1.1",),
    "AUDITORIA_INTERNA": ("3.1.3",),
    "PLAN_MEJORA": ("4.1.1",),
}


def resolver_ruta_fixture(ruta: Path | None = None) -> Path:
    """Resuelve la ruta del fixture JSON (arg, env o default)."""
    if ruta is not None:
        return ruta
    override = os.environ.get("SEED_FIXTURE_TIPOS_DOCUMENTO")
    if override:
        return Path(override)
    return FIXTURE_POR_DEFECTO


def cargar_items_fixture(ruta: Path) -> list[dict[str, Any]]:
    """Carga y valida el array `items` del fixture."""
    if not ruta.is_file():
        raise RuntimeError(
            f"No se encontró el fixture de tipos de documento: {ruta}. "
            "Verifica la ruta o ejecuta desde la raíz del repo."
        )
    try:
        payload = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Fixture JSON inválido en {ruta}: {exc}") from exc
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"El fixture {ruta} no contiene un array `items` válido.")
    return items


async def sembrar_tipos_documento_sst(
    sesion: AsyncSession,
    *,
    ruta_fixture: Path | None = None,
) -> tuple[int, int]:
    """Inserta tipos faltantes por `codigo`. Devuelve (creados, omitidos)."""
    items = cargar_items_fixture(resolver_ruta_fixture(ruta_fixture))
    creados = 0
    omitidos = 0
    for item in items:
        codigo = str(item["codigo"]).strip().upper()
        existe = (
            await sesion.execute(
                select(TipoDocumentoSstORM.id).where(TipoDocumentoSstORM.codigo == codigo)
            )
        ).scalar_one_or_none()
        if existe is not None:
            omitidos += 1
            logger.info("Tipo documento %s ya existe; se omite", codigo)
            continue
        sesion.add(
            TipoDocumentoSstORM(
                id=uuid4(),
                codigo=codigo,
                nombre=str(item["nombre"]),
                fase=str(item["fase"]).strip().upper(),
                descripcion=str(item["descripcion"]),
                obligatorio=bool(item.get("obligatorio", True)),
            )
        )
        creados += 1
        logger.info("Tipo documento %s creado", codigo)
    await sesion.flush()
    await _sembrar_vinculos_estandar(sesion)
    return creados, omitidos


async def _sembrar_vinculos_estandar(sesion: AsyncSession) -> None:
    """Crea filas tipo↔estándar faltantes; ignora numerales inexistentes."""
    for codigo, numerales in VINCULOS_TIPO_NUMERAL.items():
        tipo_id = (
            await sesion.execute(
                select(TipoDocumentoSstORM.id).where(TipoDocumentoSstORM.codigo == codigo)
            )
        ).scalar_one_or_none()
        if tipo_id is None:
            continue
        for numeral in numerales:
            estandar_id = (
                await sesion.execute(
                    select(EstandarMinimoORM.id).where(EstandarMinimoORM.numeral == numeral)
                )
            ).scalar_one_or_none()
            if estandar_id is None:
                logger.info(
                    "Numeral %s no existe; se omite vínculo con %s",
                    numeral,
                    codigo,
                )
                continue
            ya = (
                await sesion.execute(
                    select(TipoDocumentoEstandarORM.tipo_id).where(
                        TipoDocumentoEstandarORM.tipo_id == tipo_id,
                        TipoDocumentoEstandarORM.estandar_id == estandar_id,
                    )
                )
            ).scalar_one_or_none()
            if ya is not None:
                continue
            sesion.add(
                TipoDocumentoEstandarORM(
                    tipo_id=UUID(str(tipo_id)),
                    estandar_id=UUID(str(estandar_id)),
                )
            )
            logger.info("Vínculo %s ↔ %s creado", codigo, numeral)


async def principal() -> None:
    """Punto de entrada async del seed de tipos documentales."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        try:
            creados, omitidos = await sembrar_tipos_documento_sst(sesion)
            await sesion.commit()
        except Exception as exc:
            await sesion.rollback()
            raise RuntimeError(
                f"Falló el seed de tipos de documento: {exc}. "
                "¿Ejecutaste `poetry run alembic upgrade head`?"
            ) from exc
    logger.info("Tipos documento: creados=%s omitidos=%s", creados, omitidos)


if __name__ == "__main__":
    asyncio.run(principal())
