"""Genera el borrador de acciones desde los incumplimientos. Sin modelo de lenguaje."""

from uuid import UUID

from src.application.dto.respuesta_accion_mejora import RespuestaAccionMejora
from src.application.mappers.mapper_accion_mejora import MapperAccionMejora
from src.domain.exceptions.autoevaluacion import (
    AutoevaluacionNoEncontradaError,
    EstandarNoEncontradoError,
)
from src.domain.exceptions.plan_mejora import PlanMejoraNoEncontradoError
from src.domain.models.accion_mejora import AccionMejora
from src.domain.models.autoevaluacion import ResultadoCalificacion
from src.domain.models.estandar_minimo import EstandarMinimo
from src.domain.models.plan_mejora import PlanMejora
from src.domain.repositories.repositorio_accion_mejora import RepositorioAccionMejora
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.domain.repositories.repositorio_plan_mejora import RepositorioPlanMejora


class ServicioBorradorAcciones:
    """Crea una acción por cada NO_CUMPLE y no duplica el estándar."""

    def __init__(
        self,
        repositorio_plan: RepositorioPlanMejora,
        repositorio_autoevaluacion: RepositorioAutoevaluacion,
        repositorio_estandar: RepositorioEstandarMinimo,
        repositorio_accion: RepositorioAccionMejora,
    ) -> None:
        self._planes = repositorio_plan
        self._autoevaluaciones = repositorio_autoevaluacion
        self._estandares = repositorio_estandar
        self._acciones = repositorio_accion

    async def generar(self, plan_id: UUID) -> list[RespuestaAccionMejora]:
        """Agrega las acciones que faltan y devuelve el borrador completo."""
        plan = await self._exigir_plan(plan_id)
        autoevaluacion = await self._autoevaluaciones.buscar_por_id(plan.autoevaluacion_id)
        if autoevaluacion is None:
            raise AutoevaluacionNoEncontradaError()
        catalogo = await self._catalogo()
        existentes = {
            accion.estandar_id: accion for accion in await self._acciones.listar_por_plan(plan_id)
        }
        for estandar_id, calificacion in autoevaluacion.calificaciones.items():
            if calificacion.resultado != ResultadoCalificacion.NO_CUMPLE:
                continue
            if estandar_id in existentes:
                continue
            estandar = catalogo.get(estandar_id)
            if estandar is None:
                raise EstandarNoEncontradoError()
            guardada = await self._acciones.guardar(AccionMejora.crear(plan_id, estandar))
            existentes[estandar_id] = guardada
        return self._respuestas(list(existentes.values()), catalogo)

    async def listar(self, plan_id: UUID) -> list[RespuestaAccionMejora]:
        """Lee el borrador sin crear acciones."""
        await self._exigir_plan(plan_id)
        catalogo = await self._catalogo()
        acciones = await self._acciones.listar_por_plan(plan_id)
        return self._respuestas(acciones, catalogo)

    async def _exigir_plan(self, plan_id: UUID) -> PlanMejora:
        plan = await self._planes.buscar_por_id(plan_id)
        if plan is None:
            raise PlanMejoraNoEncontradoError()
        return plan

    async def _catalogo(self) -> dict[UUID, EstandarMinimo]:
        return {item.id: item for item in await self._estandares.listar()}

    def _respuestas(
        self,
        acciones: list[AccionMejora],
        catalogo: dict[UUID, EstandarMinimo],
    ) -> list[RespuestaAccionMejora]:
        pares: list[tuple[EstandarMinimo, AccionMejora]] = []
        for accion in acciones:
            estandar = catalogo.get(accion.estandar_id)
            if estandar is None:
                raise EstandarNoEncontradoError()
            pares.append((estandar, accion))
        pares.sort(key=lambda par: _clave_numeral(par[0].numeral))
        return [MapperAccionMejora.a_respuesta(accion, estandar) for estandar, accion in pares]


def _clave_numeral(numeral: str) -> tuple[tuple[int, int | str], ...]:
    """Ordena los tramos numéricos como enteros y el resto como texto."""
    clave: list[tuple[int, int | str]] = []
    for parte in numeral.split("."):
        if parte.isdigit():
            clave.append((0, int(parte)))
        else:
            clave.append((1, parte))
    return tuple(clave)
