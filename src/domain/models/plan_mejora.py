"""Agregado `PlanMejora` y actividades del cronograma anual."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.plan_mejora import (
    ActividadCronogramaInvalidaError,
    ActividadNoEncontradaError,
    AutoevaluacionEnBorradorError,
    AutoevaluacionSinPersistirError,
    PlanMejoraNoRequeridoError,
)
from src.domain.models.autoevaluacion import Autoevaluacion

LARGO_RESPONSABLE = 150
LARGO_INDICADOR = 200
MES_MINIMO = 1
MES_MAXIMO = 12


def _texto_obligatorio(valor: str, etiqueta: str, maximo: int | None = None) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ActividadCronogramaInvalidaError(f"{etiqueta} es obligatorio")
    if maximo is not None and len(limpio) > maximo:
        raise ActividadCronogramaInvalidaError(f"{etiqueta} no puede superar {maximo} caracteres")
    return limpio


def _meses_validos(meses: Iterable[int]) -> tuple[int, ...]:
    vistos: list[int] = []
    for mes in meses:
        if isinstance(mes, bool) or not isinstance(mes, int) or not MES_MINIMO <= mes <= MES_MAXIMO:
            raise ActividadCronogramaInvalidaError("El mes debe estar entre 1 y 12")
        if mes in vistos:
            raise ActividadCronogramaInvalidaError(
                "El mes no puede repetirse en la misma actividad"
            )
        vistos.append(mes)
    if not vistos:
        raise ActividadCronogramaInvalidaError("La actividad debe incluir al menos un mes")
    return tuple(sorted(vistos))


@dataclass
class ActividadCronograma:
    """Fila del cronograma: qué se hace, quién, cómo se mide y en qué meses."""

    id: UUID | None
    descripcion: str
    responsable: str
    indicador: str
    meses: tuple[int, ...]

    @classmethod
    def crear(
        cls,
        descripcion: str,
        responsable: str,
        indicador: str,
        meses: Iterable[int],
    ) -> "ActividadCronograma":
        """Valida textos y meses. El id queda vacío hasta persistir."""
        return cls(
            id=None,
            descripcion=_texto_obligatorio(descripcion, "La descripción"),
            responsable=_texto_obligatorio(responsable, "El responsable", LARGO_RESPONSABLE),
            indicador=_texto_obligatorio(indicador, "El indicador", LARGO_INDICADOR),
            meses=_meses_validos(meses),
        )


@dataclass
class PlanMejora:
    """Plan ligado a una sola autoevaluación finalizada que lo requiere."""

    id: UUID | None
    empresa_id: UUID
    autoevaluacion_id: UUID
    actividades: list[ActividadCronograma] = field(default_factory=list)
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(cls, autoevaluacion: Autoevaluacion) -> "PlanMejora":
        """Copia empresa e id. No recalcula el umbral de 85."""
        if autoevaluacion.id is None:
            raise AutoevaluacionSinPersistirError()
        if not autoevaluacion.esta_finalizada:
            raise AutoevaluacionEnBorradorError()
        if not autoevaluacion.requiere_plan_mejora:
            raise PlanMejoraNoRequeridoError()
        return cls(
            id=None,
            empresa_id=autoevaluacion.empresa_id,
            autoevaluacion_id=autoevaluacion.id,
        )

    def agregar_actividad(
        self,
        descripcion: str,
        responsable: str,
        indicador: str,
        meses: Iterable[int],
    ) -> ActividadCronograma:
        """Agrega una actividad ya validada al cronograma del plan."""
        actividad = ActividadCronograma.crear(descripcion, responsable, indicador, meses)
        self.actividades.append(actividad)
        return actividad

    def actualizar_actividad(
        self,
        actividad_id: UUID,
        descripcion: str,
        responsable: str,
        indicador: str,
        meses: Iterable[int],
    ) -> ActividadCronograma:
        """Reemplaza los datos y conserva el id de la actividad."""
        indice = self._indice_actividad(actividad_id)
        actividad = ActividadCronograma.crear(descripcion, responsable, indicador, meses)
        actividad.id = actividad_id
        self.actividades[indice] = actividad
        return actividad

    def quitar_actividad(self, actividad_id: UUID) -> None:
        """Saca la actividad del cronograma."""
        indice = self._indice_actividad(actividad_id)
        del self.actividades[indice]

    def _indice_actividad(self, actividad_id: UUID) -> int:
        for indice, actividad in enumerate(self.actividades):
            if actividad.id == actividad_id:
                return indice
        raise ActividadNoEncontradaError()
