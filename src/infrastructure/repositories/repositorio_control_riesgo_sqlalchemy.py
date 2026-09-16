"""Implementación SQLAlchemy de `RepositorioControlRiesgo`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.gtc45 import TipoControl
from src.domain.repositories.repositorio_control_riesgo import RepositorioControlRiesgo
from src.infrastructure.database.modelos.control_riesgo_orm import ControlRiesgoORM


class RepositorioControlRiesgoSQLAlchemy(RepositorioControlRiesgo):
    """Persistencia de controles — devuelve dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, control: ControlRiesgo) -> ControlRiesgo:
        fila = self._a_orm(control)
        fila = await self._sesion.merge(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def buscar_por_id(self, id: UUID) -> ControlRiesgo | None:
        fila = await self._sesion.get(ControlRiesgoORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def listar_por_evaluacion(self, evaluacion_riesgo_id: UUID) -> list[ControlRiesgo]:
        consulta = (
            select(ControlRiesgoORM)
            .where(ControlRiesgoORM.evaluacion_riesgo_id == evaluacion_riesgo_id)
            .order_by(ControlRiesgoORM.fecha_creacion)
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def eliminar(self, id: UUID) -> bool:
        fila = await self._sesion.get(ControlRiesgoORM, id)
        if fila is None:
            return False
        await self._sesion.delete(fila)
        await self._sesion.flush()
        return True

    @staticmethod
    def _a_dominio(fila: ControlRiesgoORM) -> ControlRiesgo:
        return ControlRiesgo(
            id=fila.id,
            evaluacion_riesgo_id=fila.evaluacion_riesgo_id,
            tipo=TipoControl(fila.tipo),
            descripcion=fila.descripcion,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(control: ControlRiesgo) -> ControlRiesgoORM:
        return ControlRiesgoORM(
            id=control.id if control.id is not None else uuid4(),
            evaluacion_riesgo_id=control.evaluacion_riesgo_id,
            tipo=control.tipo.value,
            descripcion=control.descripcion,
        )
