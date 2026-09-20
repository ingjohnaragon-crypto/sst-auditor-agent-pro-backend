"""Pruebas unitarias del motor de calificación Res. 0312."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from src.domain.exceptions.autoevaluacion import DatosEmpresaInvalidosError
from src.domain.models.autoevaluacion import Autoevaluacion, ResultadoCalificacion
from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.models.perfil_estandares import MapaPerfilEstandares
from src.domain.services.motor_calificacion_res312 import (
    aplicar_no_aplica_faltantes,
    calcular_cumplimiento_phva,
    numerales_no_aplican,
    orden_fases_efectivo,
    resolver_perfil_estandares,
)


def _mapa_fixture() -> MapaPerfilEstandares:
    return MapaPerfilEstandares.desde_dict(
        {
            "orden_fases_phva": ["PLANEAR", "HACER", "VERIFICAR", "ACTUAR"],
            "perfiles": {
                "TABLA_7": {
                    "prioridad": 1,
                    "regla": {
                        "min_trabajadores": 1,
                        "max_trabajadores": 10,
                        "riesgos": ["I", "II", "III"],
                    },
                    "numerales_no_aplican": ["2.2.1", "7.1.4"],
                },
                "TABLA_21": {
                    "prioridad": 2,
                    "regla": {
                        "min_trabajadores": 11,
                        "max_trabajadores": 50,
                        "riesgos": ["I", "II", "III"],
                    },
                    "numerales_no_aplican": ["7.1.4"],
                },
                "TABLA_60": {
                    "prioridad": 99,
                    "regla": {"fallback": True},
                    "numerales_no_aplican": [],
                },
            },
        }
    )


def _estandar(
    numeral: str,
    ciclo: CicloPHVA,
    valor: str,
) -> EstandarMinimo:
    return EstandarMinimo(
        id=uuid4(),
        ciclo_phva=ciclo,
        numeral=numeral,
        descripcion=f"Ítem {numeral}",
        valor_porcentual=Decimal(valor),
    )


@pytest.mark.parametrize(
    ("trabajadores", "riesgo", "esperado"),
    [
        (8, "II", "TABLA_7"),
        (10, "III", "TABLA_7"),
        (11, "III", "TABLA_21"),
        (25, "III", "TABLA_21"),
        (50, "I", "TABLA_21"),
        (51, "I", "TABLA_60"),
        (8, "IV", "TABLA_60"),
        (100, "I", "TABLA_60"),
    ],
)
def test_should_resolver_perfil_when_reglas_del_mapa(
    trabajadores: int,
    riesgo: str,
    esperado: str,
) -> None:
    mapa = _mapa_fixture()
    assert resolver_perfil_estandares(riesgo, trabajadores, mapa) == esperado


def test_should_lanzar_error_when_trabajadores_invalidos() -> None:
    with pytest.raises(DatosEmpresaInvalidosError):
        resolver_perfil_estandares("II", 0, _mapa_fixture())


def test_should_lanzar_error_when_riesgo_invalido() -> None:
    with pytest.raises(DatosEmpresaInvalidosError):
        resolver_perfil_estandares("VI", 10, _mapa_fixture())


def test_should_devolver_numerales_no_aplican_del_mapa() -> None:
    mapa = _mapa_fixture()
    assert numerales_no_aplican("TABLA_7", mapa) == frozenset({"2.2.1", "7.1.4"})
    assert numerales_no_aplican("TABLA_60", mapa) == frozenset()


def test_should_aplicar_no_aplica_solo_faltantes() -> None:
    e1 = _estandar("2.2.1", CicloPHVA.PLANEAR, "10.00")
    e2 = _estandar("7.1.4", CicloPHVA.ACTUAR, "5.00")
    e3 = _estandar("1.1.1", CicloPHVA.PLANEAR, "15.00")
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 1, 1))
    auto.calificar(e1, ResultadoCalificacion.NO_CUMPLE)

    aplicar_no_aplica_faltantes(auto, [e1, e2, e3], frozenset({"2.2.1", "7.1.4"}))

    assert auto.calificaciones[e1.id].resultado == ResultadoCalificacion.NO_CUMPLE
    assert auto.calificaciones[e1.id].puntaje == Decimal("0")
    assert auto.calificaciones[e2.id].resultado == ResultadoCalificacion.NO_APLICA
    assert auto.calificaciones[e2.id].puntaje == Decimal("5.00")
    assert e3.id not in auto.calificaciones


def test_should_calcular_phva_completo_when_todo_cumple() -> None:
    e_planear = _estandar("1.1.1", CicloPHVA.PLANEAR, "25.00")
    e_hacer = _estandar("3.1.1", CicloPHVA.HACER, "60.00")
    e_verificar = _estandar("6.1.1", CicloPHVA.VERIFICAR, "5.00")
    e_actuar = _estandar("7.1.1", CicloPHVA.ACTUAR, "10.00")
    estandares = [e_planear, e_hacer, e_verificar, e_actuar]
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 1, 1))
    for estandar in estandares:
        auto.calificar(estandar, ResultadoCalificacion.CUMPLE)
    mapa = _mapa_fixture()

    resumen = calcular_cumplimiento_phva(
        estandares,
        auto.calificaciones,
        "TABLA_60",
        frozenset(),
        mapa.orden_fases_phva,
        puntaje_total_persistido=None,
        finalizada=False,
    )

    assert resumen.puntaje_total == Decimal("100.00")
    assert resumen.requiere_plan_mejora is False
    assert len(resumen.fases) == 4
    assert [f.ciclo_phva for f in resumen.fases] == list(mapa.orden_fases_phva)
    for fase in resumen.fases:
        assert fase.porcentaje_cumplimiento == Decimal("100.00")
        assert fase.brecha == Decimal("0.00")
    assert sum((f.peso_maximo for f in resumen.fases), Decimal("0")) == Decimal("100.00")


def test_should_contar_cero_when_exigible_sin_calificar_en_preview() -> None:
    e1 = _estandar("1.1.1", CicloPHVA.PLANEAR, "50.00")
    e2 = _estandar("1.1.2", CicloPHVA.PLANEAR, "50.00")
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 1, 1))
    auto.calificar(e1, ResultadoCalificacion.CUMPLE)
    mapa = _mapa_fixture()

    resumen = calcular_cumplimiento_phva(
        [e1, e2],
        auto.calificaciones,
        "TABLA_60",
        frozenset(),
        mapa.orden_fases_phva,
        puntaje_total_persistido=None,
        finalizada=False,
    )

    fase = resumen.fases[0]
    assert fase.ciclo_phva == "PLANEAR"
    assert fase.puntaje_obtenido == Decimal("50.00")
    assert fase.porcentaje_cumplimiento == Decimal("50.00")
    assert fase.brecha == Decimal("50.00")


def test_should_simular_no_aplica_virtual_en_preview() -> None:
    e_na = _estandar("7.1.4", CicloPHVA.ACTUAR, "10.00")
    e_ex = _estandar("7.1.1", CicloPHVA.ACTUAR, "10.00")
    auto = Autoevaluacion.crear(uuid4(), uuid4(), date(2026, 1, 1))
    auto.calificar(e_ex, ResultadoCalificacion.CUMPLE)
    mapa = _mapa_fixture()

    resumen = calcular_cumplimiento_phva(
        [e_na, e_ex],
        auto.calificaciones,
        "TABLA_7",
        frozenset({"7.1.4"}),
        mapa.orden_fases_phva,
        puntaje_total_persistido=None,
        finalizada=False,
    )

    fase_actuar = next(f for f in resumen.fases if f.ciclo_phva == "ACTUAR")
    assert fase_actuar.puntaje_obtenido == Decimal("20.00")
    assert fase_actuar.porcentaje_cumplimiento == Decimal("100.00")


def test_should_derivar_orden_fases_desde_catalogo_y_mapa() -> None:
    estandares = [
        _estandar("7.1.1", CicloPHVA.ACTUAR, "10"),
        _estandar("1.1.1", CicloPHVA.PLANEAR, "10"),
    ]
    orden = orden_fases_efectivo(estandares, ("PLANEAR", "HACER", "VERIFICAR", "ACTUAR"))
    assert orden == ("PLANEAR", "HACER", "VERIFICAR", "ACTUAR")
