"""Pruebas del borrador de acciones con repositorios falsos."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from src.application.services.servicio_borrador_acciones import ServicioBorradorAcciones
from src.domain.exceptions.autoevaluacion import EstandarNoEncontradoError
from src.domain.exceptions.plan_mejora import PlanMejoraNoEncontradoError
from src.domain.models.accion_mejora import AccionMejora
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.models.plan_mejora import PlanMejora
from src.domain.repositories.repositorio_accion_mejora import RepositorioAccionMejora
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.domain.repositories.repositorio_plan_mejora import RepositorioPlanMejora


class _PlanesFalsos(RepositorioPlanMejora):
    def __init__(self, plan: PlanMejora | None) -> None:
        self.plan = plan

    async def guardar(self, plan: PlanMejora) -> PlanMejora:
        return plan

    async def buscar_por_id(self, id: UUID) -> PlanMejora | None:
        if self.plan is not None and self.plan.id == id:
            return self.plan
        return None

    async def buscar_por_autoevaluacion(self, autoevaluacion_id: UUID) -> PlanMejora | None:
        return None

    async def eliminar(self, id: UUID) -> None:
        return None


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


class _EstandaresFalsos(RepositorioEstandarMinimo):
    def __init__(self, items: list[EstandarMinimo]) -> None:
        self.items = items

    async def listar(self, ciclo_phva: CicloPHVA | None = None) -> list[EstandarMinimo]:
        return list(self.items)

    async def buscar_por_id(self, id: UUID) -> EstandarMinimo | None:
        return next((item for item in self.items if item.id == id), None)

    async def contar(self) -> int:
        return len(self.items)


class _AccionesFalsas(RepositorioAccionMejora):
    def __init__(self, iniciales: list[AccionMejora] | None = None) -> None:
        self.guardados = 0
        self.filas = list(iniciales or [])

    async def listar_por_plan(self, plan_id: UUID) -> list[AccionMejora]:
        return [accion for accion in self.filas if accion.plan_id == plan_id]

    async def guardar(self, accion: AccionMejora) -> AccionMejora:
        self.guardados += 1
        if accion.id is None:
            accion.id = uuid4()
        self.filas.append(accion)
        return accion


def _estandar(numeral: str, ciclo: CicloPHVA = CicloPHVA.HACER) -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=ciclo,
        numeral=numeral,
        descripcion=f"Ítem {numeral}",
        valor_porcentual=Decimal("1"),
    )


def _auto_con(items: list[tuple[EstandarMinimo, ResultadoCalificacion]]) -> Autoevaluacion:
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 3, 1))
    auto.id = uuid4()
    for estandar, resultado in items:
        auto.calificar(estandar, resultado)
    return auto


def _plan_de(auto: Autoevaluacion) -> PlanMejora:
    return PlanMejora(
        id=uuid4(),
        empresa_id=auto.empresa_id,
        autoevaluacion_id=auto.id,  # type: ignore[arg-type]
    )


def _servicio(
    auto: Autoevaluacion | None,
    estandares: list[EstandarMinimo],
    plan: PlanMejora | None,
    acciones: _AccionesFalsas | None = None,
) -> tuple[ServicioBorradorAcciones, _AccionesFalsas]:
    repositorio = acciones or _AccionesFalsas()
    servicio = ServicioBorradorAcciones(
        _PlanesFalsos(plan),
        _AutosFalsas(auto),
        _EstandaresFalsos(estandares),
        repositorio,
    )
    return servicio, repositorio


async def test_should_crear_solo_la_accion_del_incumplimiento() -> None:
    no_cumple = _estandar("1.1.1", CicloPHVA.PLANEAR)
    cumple = _estandar("1.1.2")
    no_aplica = _estandar("1.1.3", CicloPHVA.VERIFICAR)
    auto = _auto_con(
        [
            (no_cumple, ResultadoCalificacion.NO_CUMPLE),
            (cumple, ResultadoCalificacion.CUMPLE),
            (no_aplica, ResultadoCalificacion.NO_APLICA),
        ]
    )
    plan = _plan_de(auto)
    servicio, acciones = _servicio(auto, [no_cumple, cumple, no_aplica], plan)

    respuesta = await servicio.generar(plan.id)  # type: ignore[arg-type]

    assert acciones.guardados == 1
    assert len(respuesta) == 1
    assert respuesta[0].estandar_id == no_cumple.id
    assert respuesta[0].ciclo_phva == "PLANEAR"
    assert respuesta[0].numeral == "1.1.1"
    assert respuesta[0].responsable_sugerido is None


async def test_should_conservar_la_accion_when_el_estandar_ya_existe() -> None:
    estandar = _estandar("2.1.1", CicloPHVA.ACTUAR)
    auto = _auto_con([(estandar, ResultadoCalificacion.NO_CUMPLE)])
    plan = _plan_de(auto)
    previa = AccionMejora(
        id=uuid4(),
        plan_id=plan.id,  # type: ignore[arg-type]
        estandar_id=estandar.id,
        ciclo_phva=CicloPHVA.ACTUAR,
        responsable_sugerido="Ana",
    )
    servicio, acciones = _servicio(auto, [estandar], plan, _AccionesFalsas([previa]))

    respuesta = await servicio.generar(plan.id)  # type: ignore[arg-type]

    assert acciones.guardados == 0
    assert respuesta[0].id == previa.id
    assert respuesta[0].responsable_sugerido == "Ana"


async def test_should_ordenar_por_numeral() -> None:
    posterior = _estandar("1.1.10")
    anterior = _estandar("1.1.2")
    auto = _auto_con(
        [
            (posterior, ResultadoCalificacion.NO_CUMPLE),
            (anterior, ResultadoCalificacion.NO_CUMPLE),
        ]
    )
    plan = _plan_de(auto)
    servicio, _acciones = _servicio(auto, [posterior, anterior], plan)

    respuesta = await servicio.generar(plan.id)  # type: ignore[arg-type]

    assert [item.numeral for item in respuesta] == ["1.1.2", "1.1.10"]


async def test_should_lanzar_when_el_plan_no_existe() -> None:
    servicio, _acciones = _servicio(None, [], None)

    with pytest.raises(PlanMejoraNoEncontradoError):
        await servicio.generar(uuid4())


async def test_should_devolver_vacio_when_no_hay_incumplimientos() -> None:
    estandar = _estandar("3.1.1")
    auto = _auto_con([(estandar, ResultadoCalificacion.CUMPLE)])
    plan = _plan_de(auto)
    servicio, acciones = _servicio(auto, [estandar], plan)

    respuesta = await servicio.generar(plan.id)  # type: ignore[arg-type]

    assert acciones.guardados == 0
    assert respuesta == []


async def test_should_lanzar_when_el_estandar_no_esta_en_el_catalogo() -> None:
    estandar = _estandar("4.1.1")
    auto = _auto_con([(estandar, ResultadoCalificacion.NO_CUMPLE)])
    plan = _plan_de(auto)
    servicio, _acciones = _servicio(auto, [], plan)

    with pytest.raises(EstandarNoEncontradoError):
        await servicio.generar(plan.id)  # type: ignore[arg-type]
