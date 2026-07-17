"""Implementación SQLAlchemy del puerto `RepositorioEstandarMinimo`."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.estandar_minimo import CicloPHVA, EstandarMinimo
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.infrastructure.database.modelos.estandar_minimo_orm import EstandarMinimoORM


class RepositorioEstandarMinimoSQLAlchemy(RepositorioEstandarMinimo):
    """Lectura del catálogo `estandares_minimos` — solo dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar(self, ciclo_phva: CicloPHVA | None = None) -> list[EstandarMinimo]:
        consulta = select(EstandarMinimoORM).order_by(EstandarMinimoORM.numeral)
        if ciclo_phva is not None:
            consulta = consulta.where(EstandarMinimoORM.ciclo_phva == ciclo_phva.value)
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    async def buscar_por_id(self, id: UUID) -> EstandarMinimo | None:
        fila = await self._sesion.get(EstandarMinimoORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def contar(self) -> int:
        consulta = select(func.count()).select_from(EstandarMinimoORM)
        return int((await self._sesion.execute(consulta)).scalar_one())

    @staticmethod
    def _a_dominio(fila: EstandarMinimoORM) -> EstandarMinimo:
        return EstandarMinimo(
            id=fila.id,
            ciclo_phva=CicloPHVA(fila.ciclo_phva),
            numeral=fila.numeral,
            descripcion=fila.descripcion,
            valor_porcentual=fila.valor_porcentual,
        )
