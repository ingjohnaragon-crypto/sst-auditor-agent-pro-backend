"""Implementación SQLAlchemy del puerto `RepositorioEvidencia`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.evidencia import Evidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.infrastructure.database.modelos.calificacion_estandar_orm import (
    CalificacionEstandarORM,
)
from src.infrastructure.database.modelos.evidencia_orm import EvidenciaORM


class RepositorioEvidenciaSQLAlchemy(RepositorioEvidencia):
    """Persistencia de metadatos de evidencias."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, evidencia: Evidencia) -> Evidencia:
        fila = await self._obtener_fila(evidencia.id) if evidencia.id else None
        if fila is None:
            fila = EvidenciaORM(
                id=evidencia.id if evidencia.id is not None else uuid4(),
                calificacion_estandar_id=evidencia.calificacion_estandar_id,
                usuario_id=evidencia.usuario_id,
                nombre_archivo=evidencia.nombre_archivo,
                tipo_mime=evidencia.tipo_mime,
                tamano_bytes=evidencia.tamano_bytes,
                ruta_almacenamiento=evidencia.ruta_almacenamiento,
                fecha_carga=evidencia.fecha_carga,
                activo=evidencia.activo,
                fecha_eliminacion=evidencia.fecha_eliminacion,
            )
            self._sesion.add(fila)
        else:
            fila.activo = evidencia.activo
            fila.fecha_eliminacion = evidencia.fecha_eliminacion
            fila.fecha_actualizacion = evidencia.fecha_actualizacion
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def listar_activas_por_calificacion(
        self, calificacion_estandar_id: UUID
    ) -> list[Evidencia]:
        consulta = (
            select(EvidenciaORM)
            .where(
                EvidenciaORM.calificacion_estandar_id == calificacion_estandar_id,
                EvidenciaORM.activo.is_(True),
            )
            .order_by(EvidenciaORM.fecha_carga.desc())
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def buscar_por_id(self, id: UUID) -> Evidencia | None:
        fila = await self._obtener_fila(id)
        return self._a_dominio(fila) if fila is not None else None

    async def existe_calificacion(self, calificacion_estandar_id: UUID) -> bool:
        consulta = select(CalificacionEstandarORM.id).where(
            CalificacionEstandarORM.id == calificacion_estandar_id
        )
        return (await self._sesion.execute(consulta)).scalar_one_or_none() is not None

    async def _obtener_fila(self, id: UUID) -> EvidenciaORM | None:
        consulta = select(EvidenciaORM).where(EvidenciaORM.id == id)
        return (await self._sesion.execute(consulta)).scalar_one_or_none()

    @staticmethod
    def _a_dominio(fila: EvidenciaORM) -> Evidencia:
        return Evidencia(
            id=fila.id,
            calificacion_estandar_id=fila.calificacion_estandar_id,
            usuario_id=fila.usuario_id,
            nombre_archivo=fila.nombre_archivo,
            tipo_mime=fila.tipo_mime,
            tamano_bytes=fila.tamano_bytes,
            ruta_almacenamiento=fila.ruta_almacenamiento,
            fecha_carga=fila.fecha_carga,
            activo=fila.activo,
            fecha_eliminacion=fila.fecha_eliminacion,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
