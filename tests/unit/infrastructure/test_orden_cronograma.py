"""El mapeo del cronograma ordena actividades y meses sin ir a la base."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.infrastructure.database.modelos.actividad_cronograma_orm import (
    ActividadCronogramaORM,
)
from src.infrastructure.database.modelos.mes_actividad_orm import MesActividadORM
from src.infrastructure.database.modelos.plan_mejoramiento_orm import PlanMejoramientoORM
from src.infrastructure.repositories.repositorio_plan_mejora_sqlalchemy import (
    RepositorioPlanMejoraSQLAlchemy,
)


def test_should_ordenar_actividades_por_fecha_e_id() -> None:
    momento = datetime(2026, 3, 1, tzinfo=UTC)
    plan_id = uuid4()
    id_menor = UUID(int=1)
    id_mayor = UUID(int=2)
    id_reciente = uuid4()
    fila = PlanMejoramientoORM(
        id=plan_id,
        empresa_id=uuid4(),
        autoevaluacion_id=uuid4(),
        fecha_creacion=momento,
        fecha_actualizacion=momento,
    )
    reciente = _actividad(id_reciente, plan_id, "Reciente", datetime(2026, 4, 1, tzinfo=UTC))
    reciente.meses = [
        MesActividadORM(actividad_id=id_reciente, mes=12),
        MesActividadORM(actividad_id=id_reciente, mes=1),
    ]
    mayor = _actividad(id_mayor, plan_id, "Mayor", momento)
    mayor.meses = [MesActividadORM(actividad_id=id_mayor, mes=2)]
    menor = _actividad(id_menor, plan_id, "Menor", momento)
    menor.meses = [MesActividadORM(actividad_id=id_menor, mes=3)]
    fila.actividades = [reciente, mayor, menor]

    dominio = RepositorioPlanMejoraSQLAlchemy._a_dominio(fila)

    assert [actividad.id for actividad in dominio.actividades] == [
        id_menor,
        id_mayor,
        id_reciente,
    ]
    assert dominio.actividades[2].meses == (1, 12)


def _actividad(
    actividad_id: UUID,
    plan_id: UUID,
    descripcion: str,
    fecha_creacion: datetime,
) -> ActividadCronogramaORM:
    return ActividadCronogramaORM(
        id=actividad_id,
        plan_mejoramiento_id=plan_id,
        descripcion=descripcion,
        responsable="Ana",
        indicador="Acta",
        fecha_creacion=fecha_creacion,
        fecha_actualizacion=fecha_creacion,
    )
