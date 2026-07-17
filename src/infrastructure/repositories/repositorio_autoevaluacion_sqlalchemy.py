"""Implementación SQLAlchemy del puerto `RepositorioAutoevaluacion`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.autoevaluacion import (
    Autoevaluacion,
    CalificacionEstandar,
    ResultadoCalificacion,
)
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.infrastructure.database.modelos.autoevaluacion_orm import AutoevaluacionORM
from src.infrastructure.database.modelos.calificacion_estandar_orm import (
    CalificacionEstandarORM,
)


class RepositorioAutoevaluacionSQLAlchemy(RepositorioAutoevaluacion):
    """Persistencia del agregado `Autoevaluacion` con upsert de calificaciones."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, autoevaluacion: Autoevaluacion) -> Autoevaluacion:
        fila = await self._obtener_fila(autoevaluacion.id) if autoevaluacion.id else None
        if fila is None:
            fila = AutoevaluacionORM(
                id=autoevaluacion.id if autoevaluacion.id is not None else uuid4(),
                empresa_id=autoevaluacion.empresa_id,
                usuario_id=autoevaluacion.usuario_id,
                fecha=autoevaluacion.fecha,
                puntaje_total=autoevaluacion.puntaje_total,
                requiere_plan_mejora=autoevaluacion.requiere_plan_mejora,
            )
            self._sesion.add(fila)
        else:
            fila.empresa_id = autoevaluacion.empresa_id
            fila.usuario_id = autoevaluacion.usuario_id
            fila.fecha = autoevaluacion.fecha
            fila.puntaje_total = autoevaluacion.puntaje_total
            fila.requiere_plan_mejora = autoevaluacion.requiere_plan_mejora

        self._sincronizar_calificaciones(fila, autoevaluacion)
        await self._sesion.flush()
        # Recarga con selectinload — evita MissingGreenlet al mapear la colección.
        cargada = await self._obtener_fila(fila.id)
        assert cargada is not None
        return self._a_dominio(cargada)

    async def buscar_por_id(self, id: UUID) -> Autoevaluacion | None:
        fila = await self._obtener_fila(id)
        return self._a_dominio(fila) if fila is not None else None

    async def listar_por_empresa(self, empresa_id: UUID) -> list[Autoevaluacion]:
        consulta = (
            select(AutoevaluacionORM)
            .where(AutoevaluacionORM.empresa_id == empresa_id)
            .options(selectinload(AutoevaluacionORM.calificaciones))
            .order_by(AutoevaluacionORM.fecha.desc())
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def _obtener_fila(self, id: UUID) -> AutoevaluacionORM | None:
        consulta = (
            select(AutoevaluacionORM)
            .where(AutoevaluacionORM.id == id)
            .options(selectinload(AutoevaluacionORM.calificaciones))
        )
        return (await self._sesion.execute(consulta)).scalar_one_or_none()

    def _sincronizar_calificaciones(
        self,
        fila: AutoevaluacionORM,
        autoevaluacion: Autoevaluacion,
    ) -> None:
        """Upsert de calificaciones por `estandar_id`; elimina huérfanas del agregado."""
        por_estandar = {c.estandar_id: c for c in fila.calificaciones}
        ids_dominio = set(autoevaluacion.calificaciones.keys())

        for estandar_id, calificacion in autoevaluacion.calificaciones.items():
            existente = por_estandar.get(estandar_id)
            if existente is None:
                fila.calificaciones.append(
                    CalificacionEstandarORM(
                        id=calificacion.id if calificacion.id is not None else uuid4(),
                        estandar_id=calificacion.estandar_id,
                        resultado=calificacion.resultado.value,
                        puntaje=calificacion.puntaje,
                        observaciones=calificacion.observaciones,
                    )
                )
            else:
                existente.resultado = calificacion.resultado.value
                existente.puntaje = calificacion.puntaje
                existente.observaciones = calificacion.observaciones

        # delete-orphan elimina las filas quitadas de la colección
        for calificacion_orm in list(fila.calificaciones):
            if calificacion_orm.estandar_id not in ids_dominio:
                fila.calificaciones.remove(calificacion_orm)

    @staticmethod
    def _a_dominio(fila: AutoevaluacionORM) -> Autoevaluacion:
        calificaciones = {
            c.estandar_id: CalificacionEstandar(
                id=c.id,
                estandar_id=c.estandar_id,
                resultado=ResultadoCalificacion(c.resultado),
                puntaje=c.puntaje,
                observaciones=c.observaciones,
            )
            for c in fila.calificaciones
        }
        return Autoevaluacion(
            id=fila.id,
            empresa_id=fila.empresa_id,
            usuario_id=fila.usuario_id,
            fecha=fila.fecha,
            puntaje_total=fila.puntaje_total,
            requiere_plan_mejora=fila.requiere_plan_mejora,
            calificaciones=calificaciones,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
