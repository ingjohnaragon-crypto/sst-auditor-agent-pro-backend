"""Entidad de dominio `Peligro` — GTC 45 §2.1 paso 2."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.matriz_riesgo import DatosPeligroInvalidosError
from src.domain.models.gtc45 import ClasificacionPeligro


@dataclass
class Peligro:
    """Peligro identificado en un proceso/actividad."""

    id: UUID | None
    proceso_actividad_id: UUID
    clasificacion: ClasificacionPeligro
    descripcion: str
    efectos_posibles: str | None
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        proceso_actividad_id: UUID,
        clasificacion: str | ClasificacionPeligro,
        descripcion: str,
        efectos_posibles: str | None = None,
    ) -> "Peligro":
        """Factoría que valida clasificación y descripción."""
        try:
            clase = ClasificacionPeligro(str(clasificacion).strip().upper())
        except ValueError as exc:
            raise DatosPeligroInvalidosError(
                f"Clasificación de peligro inválida: {clasificacion}"
            ) from exc
        desc = descripcion.strip()
        if not desc:
            raise DatosPeligroInvalidosError("La descripción del peligro no puede estar vacía")
        efectos = efectos_posibles.strip() if efectos_posibles is not None else None
        if efectos is not None and not efectos:
            efectos = None
        return cls(
            id=None,
            proceso_actividad_id=proceso_actividad_id,
            clasificacion=clase,
            descripcion=desc,
            efectos_posibles=efectos,
        )

    def actualizar(
        self,
        *,
        clasificacion: str | ClasificacionPeligro | None = None,
        descripcion: str | None = None,
        efectos_posibles: str | None | object = ...,
    ) -> None:
        """Actualiza campos mutables; `efectos_posibles=...` significa sin cambio."""
        if clasificacion is not None:
            try:
                self.clasificacion = ClasificacionPeligro(str(clasificacion).strip().upper())
            except ValueError as exc:
                raise DatosPeligroInvalidosError(
                    f"Clasificación de peligro inválida: {clasificacion}"
                ) from exc
        if descripcion is not None:
            desc = descripcion.strip()
            if not desc:
                raise DatosPeligroInvalidosError("La descripción del peligro no puede estar vacía")
            self.descripcion = desc
        if efectos_posibles is not ...:
            if efectos_posibles is None:
                self.efectos_posibles = None
            else:
                efectos = str(efectos_posibles).strip()
                self.efectos_posibles = efectos if efectos else None
        self.fecha_actualizacion = datetime.now(UTC)
