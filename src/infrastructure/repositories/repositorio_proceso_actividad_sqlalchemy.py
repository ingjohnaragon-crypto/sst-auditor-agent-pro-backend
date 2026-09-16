"""Implementación SQLAlchemy de `RepositorioProcesoActividad`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.gtc45 import (
    AceptabilidadRiesgo,
    ClasificacionPeligro,
    InterpretacionNR,
    TipoControl,
)
from src.domain.models.matriz_nodos import NodoPeligroMatriz, NodoProcesoMatriz
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad
from src.domain.repositories.repositorio_proceso_actividad import (
    RepositorioProcesoActividad,
)
from src.infrastructure.database.modelos.control_riesgo_orm import ControlRiesgoORM
from src.infrastructure.database.modelos.evaluacion_riesgo_orm import EvaluacionRiesgoORM
from src.infrastructure.database.modelos.peligro_orm import PeligroORM
from src.infrastructure.database.modelos.proceso_actividad_orm import ProcesoActividadORM


class RepositorioProcesoActividadSQLAlchemy(RepositorioProcesoActividad):
    """Persistencia de procesos; devuelve dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, proceso: ProcesoActividad) -> ProcesoActividad:
        fila = self._a_orm(proceso)
        fila = await self._sesion.merge(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return self._a_dominio(fila)

    async def buscar_por_id(self, id: UUID) -> ProcesoActividad | None:
        fila = await self._sesion.get(ProcesoActividadORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def listar_por_empresa(self, empresa_id: UUID) -> list[ProcesoActividad]:
        consulta = (
            select(ProcesoActividadORM)
            .where(ProcesoActividadORM.empresa_id == empresa_id)
            .order_by(ProcesoActividadORM.nombre)
        )
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def eliminar(self, id: UUID) -> bool:
        fila = await self._sesion.get(ProcesoActividadORM, id)
        if fila is None:
            return False
        await self._sesion.delete(fila)
        await self._sesion.flush()
        return True

    async def obtener_matriz_por_empresa(self, empresa_id: UUID) -> list[NodoProcesoMatriz]:
        """Carga procesos con peligros, evaluación y controles (sin N+1)."""
        consulta = (
            select(ProcesoActividadORM)
            .where(ProcesoActividadORM.empresa_id == empresa_id)
            .options(
                selectinload(ProcesoActividadORM.peligros)
                .selectinload(PeligroORM.evaluacion)
                .selectinload(EvaluacionRiesgoORM.controles)
            )
            .order_by(ProcesoActividadORM.nombre)
        )
        filas = (await self._sesion.execute(consulta)).scalars().unique().all()
        resultado: list[NodoProcesoMatriz] = []
        for proceso_orm in filas:
            peligros_dom: list[NodoPeligroMatriz] = []
            for peligro_orm in proceso_orm.peligros:
                evaluacion_dom: EvaluacionRiesgo | None = None
                controles_dom: list[ControlRiesgo] = []
                if peligro_orm.evaluacion is not None:
                    evaluacion_dom = self._evaluacion_a_dominio(peligro_orm.evaluacion)
                    controles_dom = [
                        self._control_a_dominio(c) for c in peligro_orm.evaluacion.controles
                    ]
                peligros_dom.append(
                    NodoPeligroMatriz(
                        peligro=self._peligro_a_dominio(peligro_orm),
                        evaluacion=evaluacion_dom,
                        controles=controles_dom,
                    )
                )
            resultado.append(
                NodoProcesoMatriz(
                    proceso=self._a_dominio(proceso_orm),
                    peligros=peligros_dom,
                )
            )
        return resultado

    @staticmethod
    def _a_dominio(fila: ProcesoActividadORM) -> ProcesoActividad:
        return ProcesoActividad(
            id=fila.id,
            empresa_id=fila.empresa_id,
            nombre=fila.nombre,
            es_rutinaria=fila.es_rutinaria,
            zona_lugar=fila.zona_lugar,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(proceso: ProcesoActividad) -> ProcesoActividadORM:
        return ProcesoActividadORM(
            id=proceso.id if proceso.id is not None else uuid4(),
            empresa_id=proceso.empresa_id,
            nombre=proceso.nombre,
            es_rutinaria=proceso.es_rutinaria,
            zona_lugar=proceso.zona_lugar,
        )

    @staticmethod
    def _peligro_a_dominio(fila: PeligroORM) -> Peligro:
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
    def _evaluacion_a_dominio(fila: EvaluacionRiesgoORM) -> EvaluacionRiesgo:
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
    def _control_a_dominio(fila: ControlRiesgoORM) -> ControlRiesgo:
        return ControlRiesgo(
            id=fila.id,
            evaluacion_riesgo_id=fila.evaluacion_riesgo_id,
            tipo=TipoControl(fila.tipo),
            descripcion=fila.descripcion,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
