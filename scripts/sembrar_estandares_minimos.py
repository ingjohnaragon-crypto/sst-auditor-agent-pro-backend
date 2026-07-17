"""Seed idempotente de estándares mínimos Res. 312 de 2019.

Uso:
    poetry run python -m scripts.sembrar_estandares_minimos

Fixture por defecto: scripts/datos/estandares_minimos_res312.json
Override: SEED_FIXTURE_ESTANDARES=/ruta/alternativa.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM
from src.infrastructure.database.sesion import obtener_fabrica_sesiones

logger = logging.getLogger(__name__)

FIXTURE_POR_DEFECTO = Path(__file__).resolve().parent / "datos" / "estandares_minimos_res312.json"


def resolver_ruta_fixture(ruta: Path | None = None) -> Path:
    """Resuelve la ruta del fixture JSON (arg, env o default)."""
    if ruta is not None:
        return ruta
    override = os.environ.get("SEED_FIXTURE_ESTANDARES")
    if override:
        return Path(override)
    return FIXTURE_POR_DEFECTO


def cargar_items_fixture(ruta: Path) -> list[dict[str, Any]]:
    """Carga y valida el array `items` del fixture."""
    if not ruta.is_file():
        raise RuntimeError(
            f"No se encontró el fixture de estándares: {ruta}. "
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


async def sembrar_estandares_minimos(
    sesion: AsyncSession,
    *,
    ruta_fixture: Path | None = None,
) -> tuple[int, int]:
    """Inserta estándares faltantes por `numeral`. Devuelve (creados, omitidos)."""
    items = cargar_items_fixture(resolver_ruta_fixture(ruta_fixture))
    creados = 0
    omitidos = 0
    for item in items:
        numeral = str(item["numeral"])
        existe = (
            await sesion.execute(
                select(EstandarMinimoORM.id).where(EstandarMinimoORM.numeral == numeral)
            )
        ).scalar_one_or_none()
        if existe is not None:
            omitidos += 1
            logger.info("Estándar %s ya existe; se omite", numeral)
            continue
        sesion.add(
            EstandarMinimoORM(
                ciclo_phva=str(item["ciclo_phva"]),
                numeral=numeral,
                descripcion=str(item["descripcion"]),
                valor_porcentual=Decimal(str(item["valor_porcentual"])),
            )
        )
        creados += 1
        logger.info("Estándar %s creado", numeral)
    return creados, omitidos


async def principal() -> None:
    """Punto de entrada async del seed de estándares."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        try:
            creados, omitidos = await sembrar_estandares_minimos(sesion)
            await sesion.commit()
        except Exception as exc:
            await sesion.rollback()
            raise RuntimeError(
                f"Falló el seed de estándares mínimos: {exc}. "
                "¿Ejecutaste `poetry run alembic upgrade head`?"
            ) from exc
    logger.info(
        "Seed estándares Res. 312 finalizado: creados=%s omitidos=%s",
        creados,
        omitidos,
    )


if __name__ == "__main__":
    asyncio.run(principal())
