"""Pruebas del resumen ejecutivo: lectura de filas, sin motor ni interpretar_nr."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from src.application.services.servicio_resumen_ejecutivo import ServicioResumenEjecutivo
from src.domain.exceptions.autoevaluacion import (
    CatalogoIrrenunciableIncompletoError,
    EmpresaNoEncontradaError,
)
from src.domain.models.autoevaluacion import (
    Autoevaluacion,
    CalificacionEstandar,
    ResultadoCalificacion,
)
from src.domain.models.empresa import Empresa
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.models.evaluacion_riesgo import EvaluacionRiesgo
from src.domain.models.gtc45 import AceptabilidadRiesgo, ClasificacionPeligro, InterpretacionNR
from src.domain.models.peligro import Peligro

EMPRESA_ID = UUID("11111111-1111-1111-1111-111111111111")
USUARIO_ID = UUID("22222222-2222-2222-2222-222222222222")
ID_111 = UUID("33333333-3333-3333-3333-333333333331")
ID_114 = UUID("33333333-3333-3333-3333-333333333334")


class RepoEmpresa:
    def __init__(self, empresa: Empresa | None) -> None:
        self.empresa = empresa

    async def buscar_por_id(self, id: UUID) -> Empresa | None:
        if self.empresa is None or self.empresa.id != id:
            return None
        return self.empresa

    async def guardar(self, empresa: Empresa) -> Empresa:
        return empresa

    async def buscar_por_nit(self, nit: str) -> Empresa | None:
        return None

    async def listar(self) -> list[Empresa]:
        return []


class RepoAutoevaluacion:
    def __init__(self, items: list[Autoevaluacion]) -> None:
        self.items = items

    async def listar_por_empresa(self, empresa_id: UUID) -> list[Autoevaluacion]:
        return [item for item in self.items if item.empresa_id == empresa_id]

    async def guardar(self, autoevaluacion: Autoevaluacion) -> Autoevaluacion:
        return autoevaluacion

    async def buscar_por_id(self, id: UUID) -> Autoevaluacion | None:
        return None


class RepoEstandares:
    def __init__(self, items: list[EstandarMinimo]) -> None:
        self.items = items

    async def listar(self, ciclo_phva: CicloPHVA | None = None) -> list[EstandarMinimo]:
        return list(self.items)


class RepoProcesos:
    def __init__(self, matriz: list[dict[str, object]]) -> None:
        self.matriz = matriz

    async def obtener_matriz_por_empresa(self, empresa_id: UUID) -> list[dict[str, object]]:
        return self.matriz

    async def guardar(self, proceso: object) -> object:
        return proceso

    async def buscar_por_id(self, id: UUID) -> None:
        return None

    async def listar_por_empresa(self, empresa_id: UUID) -> list[object]:
        return []

    async def eliminar(self, id: UUID) -> bool:
        return False


def _empresa() -> Empresa:
    empresa = Empresa.crear("Acme", "900", "Metal", "II", 10)
    empresa.id = EMPRESA_ID
    return empresa


def _estandar(numeral: str, identificador: UUID, descripcion: str) -> EstandarMinimo:
    return EstandarMinimo(
        id=identificador,
        ciclo_phva=CicloPHVA.PLANEAR,
        numeral=numeral,
        descripcion=descripcion,
        valor_porcentual=Decimal("1.00"),
    )


def _catalogo() -> list[EstandarMinimo]:
    return [
        _estandar("1.1.4", ID_114, "Afiliación al sistema de riesgos laborales"),
        _estandar("1.1.1", ID_111, "Responsable del SG-SST"),
    ]


def _auto(
    fecha: date,
    creada: datetime,
    *,
    identificador: UUID | None = None,
    requiere: bool = False,
    calificaciones: dict[UUID, CalificacionEstandar] | None = None,
) -> Autoevaluacion:
    auto = Autoevaluacion.crear(EMPRESA_ID, USUARIO_ID, fecha)
    auto.id = identificador or uuid4()
    auto.fecha_creacion = creada
    auto.requiere_plan_mejora = requiere
    if calificaciones is not None:
        auto.calificaciones = calificaciones
    return auto


def _evaluacion(nivel: InterpretacionNR) -> EvaluacionRiesgo:
    return EvaluacionRiesgo(
        id=uuid4(),
        peligro_id=uuid4(),
        nivel_deficiencia=10,
        nivel_exposicion=4,
        nivel_consecuencia=100,
        nivel_probabilidad=40,
        nivel_riesgo=4000,
        interpretacion_nr=nivel,
        aceptabilidad=AceptabilidadRiesgo.NO_ACEPTABLE,
    )


def _nodo(evaluacion: EvaluacionRiesgo | None) -> dict[str, object]:
    peligro = Peligro.crear(uuid4(), ClasificacionPeligro.FISICO, "Ruido")
    return {
        "proceso": object(),
        "peligros": [{"peligro": peligro, "evaluacion": evaluacion, "controles": []}],
    }


def _servicio(
    *,
    empresa: Empresa | None = None,
    autos: list[Autoevaluacion] | None = None,
    estandares: list[EstandarMinimo] | None = None,
    matriz: list[dict[str, object]] | None = None,
) -> ServicioResumenEjecutivo:
    return ServicioResumenEjecutivo(
        repositorio_empresa=RepoEmpresa(_empresa() if empresa is None else empresa),  # type: ignore[arg-type]
        repositorio_autoevaluacion=RepoAutoevaluacion(autos or []),  # type: ignore[arg-type]
        repositorio_estandar_minimo=RepoEstandares(  # type: ignore[arg-type]
            _catalogo() if estandares is None else estandares
        ),
        repositorio_proceso=RepoProcesos(matriz or []),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_should_elegir_la_fecha_mayor_y_contar_dos() -> None:
    antigua = _auto(date(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC), requiere=True)
    reciente = _auto(date(2026, 6, 1), datetime(2026, 1, 2, tzinfo=UTC), requiere=False)
    servicio = _servicio(autos=[antigua, reciente])

    respuesta = await servicio.obtener(EMPRESA_ID)

    assert respuesta.cantidad_autoevaluaciones == 2
    assert respuesta.autoevaluacion_id == reciente.id
    assert respuesta.requiere_plan_mejora is False


@pytest.mark.asyncio
async def test_should_desempatar_por_fecha_creacion() -> None:
    primera = _auto(date(2026, 6, 1), datetime(2026, 6, 1, 8, tzinfo=UTC))
    segunda = _auto(date(2026, 6, 1), datetime(2026, 6, 1, 18, tzinfo=UTC), requiere=True)
    servicio = _servicio(autos=[primera, segunda])

    respuesta = await servicio.obtener(EMPRESA_ID)

    assert respuesta.autoevaluacion_id == segunda.id
    assert respuesta.requiere_plan_mejora is True


@pytest.mark.asyncio
async def test_should_responder_vacio_when_no_hay_autoevaluaciones() -> None:
    servicio = _servicio()

    respuesta = await servicio.obtener(EMPRESA_ID)

    assert respuesta.cantidad_autoevaluaciones == 0
    assert respuesta.autoevaluacion_id is None
    assert respuesta.requiere_plan_mejora is False
    assert [item.resultado for item in respuesta.irrenunciables] == [
        "SIN_CALIFICAR",
        "SIN_CALIFICAR",
    ]
    assert respuesta.irrenunciables[0].numeral == "1.1.1"
    assert respuesta.irrenunciables[0].descripcion == "Responsable del SG-SST"
    assert respuesta.irrenunciables[1].descripcion == "Afiliación al sistema de riesgos laborales"


@pytest.mark.asyncio
async def test_should_contar_interpretacion_persistida_e_ignorar_peligro_sin_evaluacion() -> None:
    matriz = [
        _nodo(_evaluacion(InterpretacionNR.I)),
        _nodo(_evaluacion(InterpretacionNR.II)),
        _nodo(None),
    ]
    servicio = _servicio(matriz=matriz)

    with (
        patch("src.domain.models.evaluacion_riesgo.interpretar_nr") as interpretar,
        patch("src.domain.services.motor_calificacion_res312.calcular_cumplimiento_phva") as motor,
    ):
        respuesta = await servicio.obtener(EMPRESA_ID)

    interpretar.assert_not_called()
    motor.assert_not_called()
    cuerpo = respuesta.model_dump(by_alias=True)
    assert cuerpo["distribucion_riesgos"] == {"I": 1, "II": 1, "III": 0, "IV": 0}
    assert respuesta.riesgos_nivel_i == 1
    assert respuesta.riesgos_nivel_ii == 1


@pytest.mark.asyncio
async def test_should_leer_resultado_guardado_de_irrenunciables() -> None:
    calificacion = CalificacionEstandar(
        id=uuid4(),
        estandar_id=ID_111,
        resultado=ResultadoCalificacion.NO_CUMPLE,
        puntaje=Decimal("0"),
    )
    auto = _auto(
        date(2026, 3, 1),
        datetime(2026, 3, 1, tzinfo=UTC),
        calificaciones={ID_111: calificacion},
    )
    servicio = _servicio(autos=[auto])

    respuesta = await servicio.obtener(EMPRESA_ID)

    assert respuesta.irrenunciables[0].resultado == "NO_CUMPLE"
    assert respuesta.irrenunciables[1].resultado == "SIN_CALIFICAR"


@pytest.mark.asyncio
async def test_should_lanzar_when_empresa_no_existe() -> None:
    servicio = _servicio(empresa=None)
    servicio._empresas = RepoEmpresa(None)  # type: ignore[assignment]

    with pytest.raises(EmpresaNoEncontradaError):
        await servicio.obtener(EMPRESA_ID)


@pytest.mark.asyncio
async def test_should_lanzar_when_falta_numeral_irrenunciable() -> None:
    servicio = _servicio(estandares=[_estandar("1.1.4", ID_114, "Afiliación")])

    with pytest.raises(CatalogoIrrenunciableIncompletoError):
        await servicio.obtener(EMPRESA_ID)
