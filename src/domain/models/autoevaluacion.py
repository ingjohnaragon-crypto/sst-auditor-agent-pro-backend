"""Agregado raíz `Autoevaluacion` y `CalificacionEstandar` — Res. 0312."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from src.domain.exceptions.autoevaluacion import (
    AutoevaluacionFinalizadaError,
    AutoevaluacionIncompletaError,
)
from src.domain.models.estandar_minimo import EstandarMinimo

UMBRAL_PLAN_MEJORA = Decimal("85")
TOTAL_ESTANDARES = 60
CERO = Decimal("0")


class ResultadoCalificacion(StrEnum):
    """Resultado posible al calificar un estándar mínimo."""

    CUMPLE = "CUMPLE"
    NO_CUMPLE = "NO_CUMPLE"
    NO_APLICA = "NO_APLICA"


@dataclass
class CalificacionEstandar:
    """Calificación de un ítem del catálogo dentro de una autoevaluación."""

    id: UUID | None
    estandar_id: UUID
    resultado: ResultadoCalificacion
    puntaje: Decimal
    observaciones: str | None = None

    @classmethod
    def calificar(
        cls,
        estandar: EstandarMinimo,
        resultado: ResultadoCalificacion,
        observaciones: str | None = None,
    ) -> "CalificacionEstandar":
        """Deriva el puntaje: valor del ítem si CUMPLE/NO_APLICA; 0 si NO_CUMPLE."""
        if resultado in (ResultadoCalificacion.CUMPLE, ResultadoCalificacion.NO_APLICA):
            puntaje = estandar.valor_porcentual
        else:
            puntaje = CERO
        return cls(
            id=None,
            estandar_id=estandar.id,
            resultado=resultado,
            puntaje=puntaje,
            observaciones=observaciones,
        )


@dataclass
class Autoevaluacion:
    """Autoevaluación de estándares mínimos de una empresa en una fecha."""

    id: UUID | None
    empresa_id: UUID
    usuario_id: UUID
    fecha: date
    puntaje_total: Decimal | None = None
    requiere_plan_mejora: bool = False
    calificaciones: dict[UUID, CalificacionEstandar] = field(default_factory=dict)
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(cls, empresa_id: UUID, usuario_id: UUID, fecha: date) -> "Autoevaluacion":
        """Crea una autoevaluación vacía (sin calificaciones ni puntaje)."""
        return cls(
            id=None,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            fecha=fecha,
            puntaje_total=None,
            requiere_plan_mejora=False,
            calificaciones={},
        )

    @property
    def esta_finalizada(self) -> bool:
        return self.puntaje_total is not None

    def calificar(
        self,
        estandar: EstandarMinimo,
        resultado: ResultadoCalificacion,
        observaciones: str | None = None,
    ) -> CalificacionEstandar:
        """Upsert de calificación; bloqueado si la autoevaluación ya finalizó."""
        if self.esta_finalizada:
            raise AutoevaluacionFinalizadaError()
        existente = self.calificaciones.get(estandar.id)
        calificacion = CalificacionEstandar.calificar(estandar, resultado, observaciones)
        if existente is not None and existente.id is not None:
            calificacion.id = existente.id
        self.calificaciones[estandar.id] = calificacion
        return calificacion

    def finalizar(self, total_requerido: int = TOTAL_ESTANDARES) -> None:
        """Fija puntaje_total y requiere_plan_mejora; exige todos los ítems."""
        if self.esta_finalizada:
            raise AutoevaluacionFinalizadaError()
        calificadas = len(self.calificaciones)
        if calificadas != total_requerido:
            faltantes = total_requerido - calificadas
            raise AutoevaluacionIncompletaError(
                f"Faltan {faltantes} estándar(es) por calificar ({calificadas}/{total_requerido})",
                faltantes=faltantes,
            )
        self.puntaje_total = sum(
            (c.puntaje for c in self.calificaciones.values()),
            start=CERO,
        )
        self.requiere_plan_mejora = self.puntaje_total < UMBRAL_PLAN_MEJORA
