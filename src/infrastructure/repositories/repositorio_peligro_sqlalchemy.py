"""Implementación SQLAlchemy de `RepositorioPeligro`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.gtc45 import ClasificacionPeligro
from src.domain.models.peligro import Peligro
from src.domain.repositories.repositorio_peligro import RepositorioPeligro
from src.infrastructure.database.modelos.peligro_orm import PeligroORM


class RepositorioPeligroSQLAlchemy(RepositorioPeligro):
    """Persistencia de peligros — devuelve dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, peligro: Peligro) -> Peligro:
        fila = self._a_orm(peligro)
        fila = await self._sesion.merge(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def buscar_por_id(self, id: UUID) -> Peligro | None:
        fila = await self._sesion.get(PeligroORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def listar_por_proceso(self, proceso_actividad_id: UUID) -> list[Peligro]:
        consulta = (
            select(PeligroORM)
            .where(PeligroORM.proceso_actividad_id == proceso_actividad_id)
            .order_by(PeligroORM.fecha_creacion)
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def eliminar(self, id: UUID) -> bool:
        fila = await self._sesion.get(PeligroORM, id)
        if fila is None:
            return False
        await self._sesion.delete(fila)
        await self._sesion.flush()
        return True

    @staticmethod
    def _a_dominio(fila: PeligroORM) -> Peligro:
        return Peligro(
            id=fila.id,
            proceso_actividad_id=fila.proceso_actividad_id,
            clasificacion=ClasificacionPeligro(fila.clasificacion),
            descripcion=fila.descripcion,
            efectos_posibles=fila.efectos_posibles,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(peligro: Peligro) -> PeligroORM:
        return PeligroORM(
            id=peligro.id if peligro.id is not None else uuid4(),
            proceso_actividad_id=peligro.proceso_actividad_id,
            clasificacion=peligro.clasificacion.value,
            descripcion=peligro.descripcion,
            efectos_posibles=peligro.efectos_posibles,
        )
