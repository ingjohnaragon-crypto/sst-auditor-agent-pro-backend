"""Almacenamiento de binarios: local (legado) y R2 (producción)."""

from src.infrastructure.almacenamiento.almacen_local import AlmacenLocal
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.almacenamiento.almacen_r2 import AlmacenR2, crear_almacen_r2

__all__ = [
    "AlmacenLocal",
    "AlmacenMemoria",
    "AlmacenR2",
    "crear_almacen_r2",
]
