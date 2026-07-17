"""Implementación SQLAlchemy del puerto `RepositorioEmpresa`."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions.autoevaluacion import NitDuplicadoError
from src.domain.models.empresa import Empresa
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.infrastructure.database.modelos.empresa_orm import EmpresaORM


class RepositorioEmpresaSQLAlchemy(RepositorioEmpresa):
    """Persistencia de `Empresa` sobre la tabla `empresas` — devuelve dominio, nunca ORM."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, empresa: Empresa) -> Empresa:
        fila = self._a_orm(empresa)
        try:
            fila = await self._sesion.merge(fila)
            await self._sesion.flush()
            await self._sesion.refresh(fila)
        except IntegrityError as exc:
            raise NitDuplicadoError() from exc
        return self._a_dominio(fila)

    async def buscar_por_id(self, id: UUID) -> Empresa | None:
        fila = await self._sesion.get(EmpresaORM, id)
        return self._a_dominio(fila) if fila is not None else None

    async def buscar_por_nit(self, nit: str) -> Empresa | None:
        consulta = select(EmpresaORM).where(EmpresaORM.nit == nit)
        fila = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return self._a_dominio(fila) if fila is not None else None

    async def listar(self) -> list[Empresa]:
        consulta = select(EmpresaORM).order_by(EmpresaORM.razon_social)
        filas = (await self._sesion.execute(consulta)).scalars().all()
        return [self._a_dominio(fila) for fila in filas]

    @staticmethod
    def _a_dominio(fila: EmpresaORM) -> Empresa:
        return Empresa(
            id=fila.id,
            razon_social=fila.razon_social,
            nit=fila.nit,
            actividad_economica=fila.actividad_economica,
            nivel_riesgo_arl=fila.nivel_riesgo_arl,
            numero_trabajadores=fila.numero_trabajadores,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )

    @staticmethod
    def _a_orm(empresa: Empresa) -> EmpresaORM:
        return EmpresaORM(
            id=empresa.id if empresa.id is not None else uuid4(),
            razon_social=empresa.razon_social,
            nit=empresa.nit,
            actividad_economica=empresa.actividad_economica,
            nivel_riesgo_arl=empresa.nivel_riesgo_arl,
            numero_trabajadores=empresa.numero_trabajadores,
        )
