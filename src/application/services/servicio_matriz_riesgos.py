"""Casos de uso de la matriz de riesgos GTC 45."""

from uuid import UUID

from src.application.dto.matriz_riesgo import (
    RespuestaControlRiesgo,
    RespuestaEvaluacionRiesgo,
    RespuestaMatrizRiesgos,
    RespuestaPeligro,
    RespuestaProcesoActividad,
    RespuestaProcesoMatriz,
    SolicitudActualizarControl,
    SolicitudActualizarPeligro,
    SolicitudActualizarProcesoActividad,
    SolicitudCrearControl,
    SolicitudCrearPeligro,
    SolicitudCrearProcesoActividad,
    SolicitudUpsertEvaluacion,
)
from src.application.mappers.mapper_matriz_riesgo import MapperMatrizRiesgo
from src.domain.exceptions.autoevaluacion import EmpresaNoEncontradaError
from src.domain.exceptions.matriz_riesgo import (
    ControlNoEncontradoError,
    EvaluacionNoEncontradaError,
    PeligroNoEncontradoError,
    ProcesoNoEncontradoError,
)
from src.domain.models.control_riesgo import ControlRiesgo
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.peligro import Peligro
from src.domain.models.proceso_actividad import ProcesoActividad
from src.domain.repositories.repositorio_control_riesgo import RepositorioControlRiesgo
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_evaluacion_riesgo import (
    RepositorioEvaluacionRiesgo,
)
from src.domain.repositories.repositorio_peligro import RepositorioPeligro
from src.domain.repositories.repositorio_proceso_actividad import (
    RepositorioProcesoActividad,
)


class ServicioMatrizRiesgos:
    """Orquesta persistencia de procesos, peligros, evaluaciones y controles."""

    def __init__(
        self,
        repositorio_empresa: RepositorioEmpresa,
        repositorio_proceso: RepositorioProcesoActividad,
        repositorio_peligro: RepositorioPeligro,
        repositorio_evaluacion: RepositorioEvaluacionRiesgo,
        repositorio_control: RepositorioControlRiesgo,
    ) -> None:
        self._empresas = repositorio_empresa
        self._procesos = repositorio_proceso
        self._peligros = repositorio_peligro
        self._evaluaciones = repositorio_evaluacion
        self._controles = repositorio_control

    async def _exigir_empresa(self, empresa_id: UUID) -> None:
        if await self._empresas.buscar_por_id(empresa_id) is None:
            raise EmpresaNoEncontradaError()

    async def _exigir_proceso(self, proceso_id: UUID) -> ProcesoActividad:
        proceso = await self._procesos.buscar_por_id(proceso_id)
        if proceso is None:
            raise ProcesoNoEncontradoError()
        return proceso

    async def _exigir_peligro(self, peligro_id: UUID) -> Peligro:
        peligro = await self._peligros.buscar_por_id(peligro_id)
        if peligro is None:
            raise PeligroNoEncontradoError()
        return peligro

    async def _exigir_evaluacion(self, evaluacion_id: UUID) -> EvaluacionRiesgo:
        evaluacion = await self._evaluaciones.buscar_por_id(evaluacion_id)
        if evaluacion is None:
            raise EvaluacionNoEncontradaError()
        return evaluacion

    async def listar_procesos(self, empresa_id: UUID) -> list[RespuestaProcesoActividad]:
        await self._exigir_empresa(empresa_id)
        procesos = await self._procesos.listar_por_empresa(empresa_id)
        return [MapperMatrizRiesgo.proceso_a_respuesta(p) for p in procesos]

    async def crear_proceso(
        self, empresa_id: UUID, dto: SolicitudCrearProcesoActividad
    ) -> RespuestaProcesoActividad:
        await self._exigir_empresa(empresa_id)
        proceso = ProcesoActividad.crear(
            empresa_id=empresa_id,
            nombre=dto.nombre,
            es_rutinaria=dto.es_rutinaria,
            zona_lugar=dto.zona_lugar,
        )
        guardado = await self._procesos.guardar(proceso)
        return MapperMatrizRiesgo.proceso_a_respuesta(guardado)

    async def obtener_proceso(self, proceso_id: UUID) -> RespuestaProcesoActividad:
        proceso = await self._exigir_proceso(proceso_id)
        return MapperMatrizRiesgo.proceso_a_respuesta(proceso)

    async def actualizar_proceso(
        self, proceso_id: UUID, dto: SolicitudActualizarProcesoActividad
    ) -> RespuestaProcesoActividad:
        proceso = await self._exigir_proceso(proceso_id)
        campos = dto.model_dump(exclude_unset=True)
        proceso.actualizar(
            nombre=campos.get("nombre"),
            es_rutinaria=campos.get("es_rutinaria"),
            zona_lugar=campos["zona_lugar"] if "zona_lugar" in campos else ...,
        )
        guardado = await self._procesos.guardar(proceso)
        return MapperMatrizRiesgo.proceso_a_respuesta(guardado)

    async def eliminar_proceso(self, proceso_id: UUID) -> None:
        if not await self._procesos.eliminar(proceso_id):
            raise ProcesoNoEncontradoError()

    async def listar_peligros(self, proceso_id: UUID) -> list[RespuestaPeligro]:
        await self._exigir_proceso(proceso_id)
        peligros = await self._peligros.listar_por_proceso(proceso_id)
        return [MapperMatrizRiesgo.peligro_a_respuesta(p) for p in peligros]

    async def crear_peligro(self, proceso_id: UUID, dto: SolicitudCrearPeligro) -> RespuestaPeligro:
        await self._exigir_proceso(proceso_id)
        peligro = Peligro.crear(
            proceso_actividad_id=proceso_id,
            clasificacion=dto.clasificacion,
            descripcion=dto.descripcion,
            efectos_posibles=dto.efectos_posibles,
        )
        guardado = await self._peligros.guardar(peligro)
        return MapperMatrizRiesgo.peligro_a_respuesta(guardado)

    async def obtener_peligro(self, peligro_id: UUID) -> RespuestaPeligro:
        peligro = await self._exigir_peligro(peligro_id)
        return MapperMatrizRiesgo.peligro_a_respuesta(peligro)

    async def actualizar_peligro(
        self, peligro_id: UUID, dto: SolicitudActualizarPeligro
    ) -> RespuestaPeligro:
        peligro = await self._exigir_peligro(peligro_id)
        campos = dto.model_dump(exclude_unset=True)
        peligro.actualizar(
            clasificacion=campos.get("clasificacion"),
            descripcion=campos.get("descripcion"),
            efectos_posibles=(campos["efectos_posibles"] if "efectos_posibles" in campos else ...),
        )
        guardado = await self._peligros.guardar(peligro)
        return MapperMatrizRiesgo.peligro_a_respuesta(guardado)

    async def eliminar_peligro(self, peligro_id: UUID) -> None:
        if not await self._peligros.eliminar(peligro_id):
            raise PeligroNoEncontradoError()

    async def obtener_evaluacion(self, peligro_id: UUID) -> RespuestaEvaluacionRiesgo:
        await self._exigir_peligro(peligro_id)
        evaluacion = await self._evaluaciones.buscar_por_peligro(peligro_id)
        if evaluacion is None:
            raise EvaluacionNoEncontradaError()
        return MapperMatrizRiesgo.evaluacion_a_respuesta(evaluacion)

    async def upsert_evaluacion(
        self, peligro_id: UUID, dto: SolicitudUpsertEvaluacion
    ) -> tuple[RespuestaEvaluacionRiesgo, bool]:
        """Retorna (respuesta, creado)."""
        await self._exigir_peligro(peligro_id)
        existente = await self._evaluaciones.buscar_por_peligro(peligro_id)
        if existente is None:
            evaluacion = EvaluacionRiesgo.crear(
                peligro_id=peligro_id,
                nivel_deficiencia=dto.nivel_deficiencia,
                nivel_exposicion=dto.nivel_exposicion,
                nivel_consecuencia=dto.nivel_consecuencia,
            )
            creado = True
        else:
            existente.recalcular(
                dto.nivel_deficiencia,
                dto.nivel_exposicion,
                dto.nivel_consecuencia,
            )
            evaluacion = existente
            creado = False
        guardada = await self._evaluaciones.guardar(evaluacion)
        return MapperMatrizRiesgo.evaluacion_a_respuesta(guardada), creado

    async def listar_controles(self, evaluacion_id: UUID) -> list[RespuestaControlRiesgo]:
        await self._exigir_evaluacion(evaluacion_id)
        controles = await self._controles.listar_por_evaluacion(evaluacion_id)
        return [MapperMatrizRiesgo.control_a_respuesta(c) for c in controles]

    async def crear_control(
        self, evaluacion_id: UUID, dto: SolicitudCrearControl
    ) -> RespuestaControlRiesgo:
        await self._exigir_evaluacion(evaluacion_id)
        control = ControlRiesgo.crear(
            evaluacion_riesgo_id=evaluacion_id,
            tipo=dto.tipo,
            descripcion=dto.descripcion,
        )
        guardado = await self._controles.guardar(control)
        return MapperMatrizRiesgo.control_a_respuesta(guardado)

    async def actualizar_control(
        self, control_id: UUID, dto: SolicitudActualizarControl
    ) -> RespuestaControlRiesgo:
        control = await self._controles.buscar_por_id(control_id)
        if control is None:
            raise ControlNoEncontradoError()
        campos = dto.model_dump(exclude_unset=True)
        control.actualizar(
            tipo=campos.get("tipo"),
            descripcion=campos.get("descripcion"),
        )
        guardado = await self._controles.guardar(control)
        return MapperMatrizRiesgo.control_a_respuesta(guardado)

    async def eliminar_control(self, control_id: UUID) -> None:
        if not await self._controles.eliminar(control_id):
            raise ControlNoEncontradoError()

    async def obtener_matriz(self, empresa_id: UUID) -> RespuestaMatrizRiesgos:
        await self._exigir_empresa(empresa_id)
        nodos = await self._procesos.obtener_matriz_por_empresa(empresa_id)
        procesos_resp: list[RespuestaProcesoMatriz] = []
        for nodo in nodos:
            peligros_resp = [
                MapperMatrizRiesgo.nodo_peligro_a_respuesta(
                    item["peligro"],
                    item["evaluacion"],
                    item["controles"],
                )
                for item in nodo["peligros"]
            ]
            procesos_resp.append(
                MapperMatrizRiesgo.nodo_proceso_a_respuesta(nodo["proceso"], peligros_resp)
            )
        return RespuestaMatrizRiesgos(empresa_id=empresa_id, procesos=procesos_resp)
