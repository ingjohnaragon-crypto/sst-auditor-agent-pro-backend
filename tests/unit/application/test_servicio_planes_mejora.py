"""Pruebas del servicio de planes de mejora con repositorios falsos."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from src.application.dto.solicitud_plan_mejora import (
    SolicitudAbrirPlanMejora,
    SolicitudActividadCronograma,
)
from src.application.services.servicio_planes_mejora import ServicioPlanesMejora
from src.domain.exceptions.autoevaluacion import AutoevaluacionNoEncontradaError
from src.domain.exceptions.plan_mejora import (
    ActividadCronogramaInvalidaError,
    ActividadNoEncontradaError,
    AutoevaluacionEnBorradorError,
    PlanMejoraNoRequeridoError,
    PlanMejoraYaExisteError,
)
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.models.plan_mejora import PlanMejora
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_plan_mejora import RepositorioPlanMejora


class _PlanesFalsos(RepositorioPlanMejora):
    def __init__(self, inicial: PlanMejora | None = None) -> None:
        self.guardados = 0
        self.eliminados = 0
        self.por_id: dict[UUID, PlanMejora] = {}
        self.por_auto: dict[UUID, PlanMejora] = {}
        if inicial is not None and inicial.id is not None:
            self.por_id[inicial.id] = inicial
            self.por_auto[inicial.autoevaluacion_id] = inicial

    async def guardar(self, plan: PlanMejora) -> PlanMejora:
        self.guardados += 1
        if plan.id is None:
            plan.id = uuid4()
        for actividad in plan.actividades:
            if actividad.id is None:
                actividad.id = uuid4()
        self.por_id[plan.id] = plan
        self.por_auto[plan.autoevaluacion_id] = plan
        return plan

    async def buscar_por_id(self, id: UUID) -> PlanMejora | None:
        return self.por_id.get(id)

    async def buscar_por_autoevaluacion(self, autoevaluacion_id: UUID) -> PlanMejora | None:
        return self.por_auto.get(autoevaluacion_id)

    async def eliminar(self, id: UUID) -> None:
        self.eliminados += 1
        plan = self.por_id.pop(id, None)
        if plan is not None:
            self.por_auto.pop(plan.autoevaluacion_id, None)


class _AutosFalsas(RepositorioAutoevaluacion):
    def __init__(self, auto: Autoevaluacion | None) -> None:
        self.auto = auto

    async def guardar(self, autoevaluacion: Autoevaluacion) -> Autoevaluacion:
        return autoevaluacion

    async def buscar_por_id(self, id: UUID) -> Autoevaluacion | None:
        if self.auto is not None and self.auto.id == id:
            return self.auto
        return None

    async def listar_por_empresa(self, empresa_id: UUID) -> list[Autoevaluacion]:
        return []


def _estandar(valor: str) -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral="1.1.1",
        descripcion="Ítem",
        valor_porcentual=Decimal(valor),
    )


def _finalizada(valor: str) -> Autoevaluacion:
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 3, 1))
    auto.calificar(_estandar(valor), ResultadoCalificacion.CUMPLE)
    auto.finalizar(total_requerido=1)
    auto.id = uuid4()
    return auto


def _servicio(
    auto: Autoevaluacion | None,
    planes: _PlanesFalsos | None = None,
) -> tuple[ServicioPlanesMejora, _PlanesFalsos]:
    repositorio = planes or _PlanesFalsos()
    return (
        ServicioPlanesMejora(repositorio, _AutosFalsas(auto)),
        repositorio,
    )


def _actividad(meses: list[int] | None = None) -> SolicitudActividadCronograma:
    return SolicitudActividadCronograma(
        descripcion="Capacitar",
        responsable="Jefe SST",
        indicador="Listado",
        meses=meses if meses is not None else [1],
    )


async def test_should_guardar_plan_when_la_autoevaluacion_lo_exige() -> None:
    auto = _finalizada("84.99")
    servicio, planes = _servicio(auto)

    respuesta = await servicio.abrir(
        auto.id,  # type: ignore[arg-type]
        SolicitudAbrirPlanMejora(actividades=[_actividad([12, 1])]),
    )

    assert planes.guardados == 1
    assert respuesta.empresa_id == auto.empresa_id
    assert respuesta.autoevaluacion_id == auto.id
    assert respuesta.actividades[0].meses == [1, 12]


async def test_should_abrir_plan_vacio_when_no_hay_actividades() -> None:
    auto = _finalizada("84.99")
    servicio, planes = _servicio(auto)

    respuesta = await servicio.abrir(auto.id, SolicitudAbrirPlanMejora())  # type: ignore[arg-type]

    assert planes.guardados == 1
    assert respuesta.actividades == []


async def test_should_no_guardar_when_no_requiere_plan() -> None:
    auto = _finalizada("85.00")
    servicio, planes = _servicio(auto)

    with pytest.raises(PlanMejoraNoRequeridoError):
        await servicio.abrir(auto.id, SolicitudAbrirPlanMejora())  # type: ignore[arg-type]

    assert planes.guardados == 0


async def test_should_no_guardar_when_esta_en_borrador() -> None:
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 3, 1))
    auto.id = uuid4()
    servicio, planes = _servicio(auto)

    with pytest.raises(AutoevaluacionEnBorradorError):
        await servicio.abrir(auto.id, SolicitudAbrirPlanMejora())

    assert planes.guardados == 0


async def test_should_lanzar_when_autoevaluacion_no_existe() -> None:
    servicio, planes = _servicio(None)

    with pytest.raises(AutoevaluacionNoEncontradaError):
        await servicio.abrir(uuid4(), SolicitudAbrirPlanMejora())

    assert planes.guardados == 0


async def test_should_no_guardar_when_el_plan_ya_existe() -> None:
    auto = _finalizada("84.99")
    previo = PlanMejora.crear(auto)
    previo.id = uuid4()
    servicio, planes = _servicio(auto, _PlanesFalsos(previo))

    with pytest.raises(PlanMejoraYaExisteError):
        await servicio.abrir(auto.id, SolicitudAbrirPlanMejora())  # type: ignore[arg-type]

    assert planes.guardados == 0


async def test_should_lanzar_when_el_mes_es_invalido() -> None:
    auto = _finalizada("84.99")
    servicio, planes = _servicio(auto)

    with pytest.raises(ActividadCronogramaInvalidaError):
        await servicio.abrir(
            auto.id,  # type: ignore[arg-type]
            SolicitudAbrirPlanMejora(actividades=[_actividad([13])]),
        )

    assert planes.guardados == 0


async def test_should_actualizar_actividad_conservando_el_id() -> None:
    auto = _finalizada("84.99")
    plan = PlanMejora.crear(auto)
    actividad = plan.agregar_actividad("Capacitar", "Jefe SST", "Listado", [1])
    plan.id = uuid4()
    actividad.id = uuid4()
    servicio, _planes = _servicio(auto, _PlanesFalsos(plan))

    respuesta = await servicio.actualizar_actividad(
        plan.id,
        actividad.id,
        SolicitudActividadCronograma(
            descripcion="Reentrenar",
            responsable="Jefe SST",
            indicador="Acta",
            meses=[2],
        ),
    )

    assert respuesta.actividades[0].id == actividad.id
    assert respuesta.actividades[0].descripcion == "Reentrenar"
    assert respuesta.actividades[0].meses == [2]


async def test_should_quitar_actividad_when_el_id_existe() -> None:
    auto = _finalizada("84.99")
    plan = PlanMejora.crear(auto)
    actividad = plan.agregar_actividad("Capacitar", "Jefe SST", "Listado", [1])
    plan.id = uuid4()
    actividad.id = uuid4()
    servicio, planes = _servicio(auto, _PlanesFalsos(plan))

    await servicio.quitar_actividad(plan.id, actividad.id)

    assert planes.por_id[plan.id].actividades == []


async def test_should_lanzar_when_la_actividad_no_esta() -> None:
    auto = _finalizada("84.99")
    plan = PlanMejora.crear(auto)
    plan.id = uuid4()
    servicio, _planes = _servicio(auto, _PlanesFalsos(plan))

    with pytest.raises(ActividadNoEncontradaError):
        await servicio.quitar_actividad(plan.id, uuid4())
