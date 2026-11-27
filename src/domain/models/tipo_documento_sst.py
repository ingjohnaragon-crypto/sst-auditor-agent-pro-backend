"""Catálogo de tipos documentales del ciclo PHVA (SG-SST)."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class FaseDocumentoPhva(StrEnum):
    """Fase del ciclo PHVA para un tipo de documento obligatorio."""

    PLANEAR = "PLANEAR"
    HACER = "HACER"
    VERIFICAR = "VERIFICAR"
    ACTUAR = "ACTUAR"


class TipoDocumentoSst:
    """Tipo de documento del catálogo (solo lectura tras la semilla)."""

    def __init__(
        self,
        *,
        id: UUID | None,
        codigo: str,
        nombre: str,
        fase: FaseDocumentoPhva,
        descripcion: str,
        obligatorio: bool = True,
    ) -> None:
        self.id = id
        self.codigo = codigo
        self.nombre = nombre
        self.fase = fase
        self.descripcion = descripcion
        self.obligatorio = obligatorio
