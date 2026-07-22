"""Entidad de dominio `ProcesoActividad` — GTC 45 §2.1 paso 1."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.matriz_riesgo import DatosProcesoInvalidosError


@dataclass
class ProcesoActividad:
    """Proceso o actividad rutinaria/no rutinaria de una empresa."""

    id: UUID | None
    empresa_id: UUID
    nombre: str
    es_rutinaria: bool
    zona_lugar: str | None
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        empresa_id: UUID,
        nombre: str,
        es_rutinaria: bool,
        zona_lugar: str | None = None,
    ) -> "ProcesoActividad":
        """Factoría que valida invariantes de negocio."""
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            raise DatosProcesoInvalidosError("El nombre del proceso no puede estar vacío")
        zona = zona_lugar.strip() if zona_lugar is not None else None
        if zona is not None and not zona:
            zona = None
        return cls(
            id=None,
            empresa_id=empresa_id,
            nombre=nombre_limpio,
            es_rutinaria=es_rutinaria,
            zona_lugar=zona,
        )

    def actualizar(
        self,
        *,
        nombre: str | None = None,
        es_rutinaria: bool | None = None,
        zona_lugar: str | None | object = ...,
    ) -> None:
        """Actualiza campos mutables; `zona_lugar=...` significa sin cambio."""
        if nombre is not None:
            nombre_limpio = nombre.strip()
            if not nombre_limpio:
                raise DatosProcesoInvalidosError("El nombre del proceso no puede estar vacío")
            self.nombre = nombre_limpio
        if es_rutinaria is not None:
            self.es_rutinaria = es_rutinaria
        if zona_lugar is not ...:
            if zona_lugar is None:
                self.zona_lugar = None
            else:
                zona = str(zona_lugar).strip()
                self.zona_lugar = zona if zona else None
        self.fecha_actualizacion = datetime.now(UTC)
