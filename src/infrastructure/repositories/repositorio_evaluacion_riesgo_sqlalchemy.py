"""Implementación SQLAlchemy de `RepositorioEvaluacionRiesgo`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.gtc45 import AceptabilidadRiesgo, InterpretacionNR
from src.domain.repositories.repositorio_evaluacion_riesgo import (
    RepositorioEvaluacionRiesgo,
)
from src.infrastructure.database.modelos.evaluacion_riesgo_orm import EvaluacionRiesgoORM


class RepositorioEvaluacionRiesgoSQLAlchemy(RepositorioEvaluacionRiesgo):
    """Persistencia de evaluaciones — upsert por peligro_id."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, evaluacion: EvaluacionRiesgo) -> EvaluacionRiesgo:
        existente = await self.buscar_por_peligro(evaluacion.peligro_id)
        if existente is not None:
            evaluacion.id = existente.id
            evaluacion.fecha_creacion = existente.fecha_creacion
        fila = self._a_orm(evaluacion)
        fila = await self._sesion.merge(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def buscar_por_id(self, id: UUID) -> EvaluacionRiesgo | None:
        fila = await self._sesion.get(EvaluacionRiesgoORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def buscar_por_peligro(self, peligro_id: UUID) -> EvaluacionRiesgo | None:
        consulta = select(EvaluacionRiesgoORM).where(EvaluacionRiesgoORM.peligro_id == peligro_id)
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    @staticmethod
    def _a_dominio(fila: EvaluacionRiesgoORM) -> EvaluacionRiesgo:
        return EvaluacionRiesgo(
            id=fila.id,
            peligro_id=fila.peligro_id,
            nivel_deficiencia=fila.nivel_deficiencia,
            nivel_exposicion=fila.nivel_exposicion,
            nivel_consecuencia=fila.nivel_consecuencia,
            nivel_probabilidad=fila.nivel_probabilidad,
            nivel_riesgo=fila.nivel_riesgo,
            interpretacion_nr=InterpretacionNR(fila.interpretacion_nr),
            aceptabilidad=AceptabilidadRiesgo(fila.aceptabilidad),
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(evaluacion: EvaluacionRiesgo) -> EvaluacionRiesgoORM:
        return EvaluacionRiesgoORM(
            id=evaluacion.id if evaluacion.id is not None else uuid4(),
            peligro_id=evaluacion.peligro_id,
            nivel_deficiencia=evaluacion.nivel_deficiencia,
            nivel_exposicion=evaluacion.nivel_exposicion,
            nivel_consecuencia=evaluacion.nivel_consecuencia,
            nivel_probabilidad=evaluacion.nivel_probabilidad,
            nivel_riesgo=evaluacion.nivel_riesgo,
            interpretacion_nr=evaluacion.interpretacion_nr.value,
            aceptabilidad=evaluacion.aceptabilidad.value,
        )
