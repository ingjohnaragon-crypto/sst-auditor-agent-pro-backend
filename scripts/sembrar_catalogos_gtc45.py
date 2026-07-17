"""Seed idempotente de catálogos GTC 45 (Anexos A/B + D1).

Uso:
    poetry run python -m scripts.sembrar_catalogos_gtc45

Fixture por defecto: scripts/datos/catalogos_gtc45.json
Override: SEED_FIXTURE_CATALOGOS=/ruta/alternativa.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.modelos.catalogo_referencia_orm import CatalogoReferenciaORM
from src.infrastructure.database.sesion import obtener_fabrica_sesiones

logger = logging.getLogger(__name__)

FIXTURE_POR_DEFECTO = Path(__file__).resolve().parent / "datos" / "catalogos_gtc45.json"


def resolver_ruta_fixture(ruta: Path | None = None) -> Path:
    """Resuelve la ruta del fixture JSON (arg, env o default)."""
    if ruta is not None:
        return ruta
    override = os.environ.get("SEED_FIXTURE_CATALOGOS")
    if override:
        return Path(override)
    return FIXTURE_POR_DEFECTO


def cargar_items_fixture(ruta: Path) -> list[dict[str, Any]]:
    """Carga y valida el array `items` del fixture."""
    if not ruta.is_file():
        raise RuntimeError(
            f"No se encontró el fixture de catálogos GTC 45: {ruta}. "
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


async def sembrar_catalogos_gtc45(
    sesion: AsyncSession,
    *,
    ruta_fixture: Path | None = None,
) -> tuple[int, int]:
    """Inserta catálogos faltantes por (`tipo`, `codigo`). Devuelve (creados, omitidos)."""
    items = cargar_items_fixture(resolver_ruta_fixture(ruta_fixture))
    creados = 0
    omitidos = 0
    for item in items:
        tipo = str(item["tipo"])
        codigo = str(item["codigo"])
        existe = (
            await sesion.execute(
                select(CatalogoReferenciaORM.id).where(
                    CatalogoReferenciaORM.tipo == tipo,
                    CatalogoReferenciaORM.codigo == codigo,
                )
            )
        ).scalar_one_or_none()
        if existe is not None:
            omitidos += 1
            logger.info("Catálogo %s/%s ya existe; se omite", tipo, codigo)
            continue
        valor = item.get("valor_numerico")
        sesion.add(
            CatalogoReferenciaORM(
                tipo=tipo,
                codigo=codigo,
                valor_numerico=int(valor) if valor is not None else None,
                etiqueta=str(item["etiqueta"]),
                descripcion=str(item["descripcion"]),
                orden=int(item.get("orden", 0)),
            )
        )
        creados += 1
        logger.info("Catálogo %s/%s creado", tipo, codigo)
    return creados, omitidos


async def principal() -> None:
    """Punto de entrada async del seed GTC 45."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    fabrica = obtener_fabrica_sesiones()
    async with fabrica() as sesion:
        try:
            creados, omitidos = await sembrar_catalogos_gtc45(sesion)
            await sesion.commit()
        except Exception as exc:
            await sesion.rollback()
            raise RuntimeError(
                f"Falló el seed de catálogos GTC 45: {exc}. "
                "¿Ejecutaste `poetry run alembic upgrade head`?"
            ) from exc
    logger.info(
        "Seed catálogos GTC 45 finalizado: creados=%s omitidos=%s",
        creados,
        omitidos,
    )


if __name__ == "__main__":
    asyncio.run(principal())
