"""Casos de uso de autoevaluación Res. 0312 — sin FastAPI ni SQLAlchemy."""

from uuid import UUID

from src.application.dto.respuesta_autoevaluacion import RespuestaAutoevaluacion
from src.application.dto.respuesta_calificacion_estandar import (
    RespuestaCalificacionEstandar,
)
from src.application.dto.respuesta_estandar_minimo import RespuestaEstandarMinimo
from src.application.dto.solicitud_calificar_estandar import SolicitudCalificarEstandar
from src.application.dto.solicitud_crear_autoevaluacion import (
    SolicitudCrearAutoevaluacion,
)
from src.application.mappers.mapper_autoevaluacion import MapperAutoevaluacion
from src.application.mappers.mapper_estandar_minimo import MapperEstandarMinimo
from src.domain.exceptions.autoevaluacion import (
    AutoevaluacionNoEncontradaError,
    EmpresaNoEncontradaError,
    EstandarNoEncontradoError,
)
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo


class ServicioAutoevaluaciones:
    """Casos de uso de autoevaluación, calificación, finalización y catálogo."""

    def __init__(
        self,
        repositorio_autoevaluacion: RepositorioAutoevaluacion,
        repositorio_empresa: RepositorioEmpresa,
        repositorio_estandar_minimo: RepositorioEstandarMinimo,
    ) -> None:
        self._autoevaluaciones = repositorio_autoevaluacion
        self._empresas = repositorio_empresa
        self._estandares = repositorio_estandar_minimo

    async def crear(
        self, dto: SolicitudCrearAutoevaluacion, usuario_id: UUID
    ) -> RespuestaAutoevaluacion:
        """Inicia una autoevaluación; exige que la empresa exista."""
        empresa = await self._empresas.buscar_por_id(dto.empresa_id)
        if empresa is None:
            raise EmpresaNoEncontradaError()
        autoevaluacion = Autoevaluacion.crear(
            empresa_id=dto.empresa_id,
            usuario_id=usuario_id,
            fecha=dto.fecha,
        )
        guardada = await self._autoevaluaciones.guardar(autoevaluacion)
        return MapperAutoevaluacion.a_respuesta(guardada)

    async def listar_por_empresa(self, empresa_id: UUID) -> list[RespuestaAutoevaluacion]:
        """Histórico de autoevaluaciones (fecha desc); sin calificaciones embebidas."""
        autoevaluaciones = await self._autoevaluaciones.listar_por_empresa(empresa_id)
        return [
            MapperAutoevaluacion.a_respuesta(a, incluir_calificaciones=False)
            for a in autoevaluaciones
        ]

    async def obtener(self, id: UUID) -> RespuestaAutoevaluacion:
        """Detalle con calificaciones; `None` → `AutoevaluacionNoEncontradaError`."""
        autoevaluacion = await self._autoevaluaciones.buscar_por_id(id)
        if autoevaluacion is None:
            raise AutoevaluacionNoEncontradaError()
        return MapperAutoevaluacion.a_respuesta(autoevaluacion)

    async def calificar(
        self,
        autoevaluacion_id: UUID,
        estandar_id: UUID,
        dto: SolicitudCalificarEstandar,
    ) -> RespuestaCalificacionEstandar:
        """Upsert de calificación; deriva el puntaje en dominio."""
        autoevaluacion = await self._autoevaluaciones.buscar_por_id(autoevaluacion_id)
        if autoevaluacion is None:
            raise AutoevaluacionNoEncontradaError()
        estandar = await self._estandares.buscar_por_id(estandar_id)
        if estandar is None:
            raise EstandarNoEncontradoError()
        calificacion = autoevaluacion.calificar(
            estandar,
            ResultadoCalificacion(dto.resultado),
            dto.observaciones,
        )
        await self._autoevaluaciones.guardar(autoevaluacion)
        return MapperAutoevaluacion.a_respuesta_calificacion(calificacion)

    async def finalizar(self, autoevaluacion_id: UUID) -> RespuestaAutoevaluacion:
        """Cierra la autoevaluación usando el total del catálogo como exigencia."""
        autoevaluacion = await self._autoevaluaciones.buscar_por_id(autoevaluacion_id)
        if autoevaluacion is None:
            raise AutoevaluacionNoEncontradaError()
        total_requerido = await self._estandares.contar()
        autoevaluacion.finalizar(total_requerido=total_requerido)
        guardada = await self._autoevaluaciones.guardar(autoevaluacion)
        return MapperAutoevaluacion.a_respuesta(guardada)

    async def listar_estandares(
        self, ciclo_phva: CicloPHVA | None = None
    ) -> list[RespuestaEstandarMinimo]:
        """Lista el catálogo de estándares mínimos, opcionalmente filtrado."""
        estandares = await self._estandares.listar(ciclo_phva)
        return [MapperEstandarMinimo.a_respuesta(e) for e in estandares]
