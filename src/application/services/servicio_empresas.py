"""Casos de uso de empresas — orquesta el puerto `RepositorioEmpresa`."""

from uuid import UUID

from src.application.dto.respuesta_empresa import RespuestaEmpresa
from src.application.dto.solicitud_crear_empresa import SolicitudCrearEmpresa
from src.application.mappers.mapper_empresa import MapperEmpresa
from src.domain.exceptions.autoevaluacion import (
    EmpresaNoEncontradaError,
    NitDuplicadoError,
)
from src.domain.models.empresa import Empresa
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa


class ServicioEmpresas:
    """Casos de uso: crear, listar y obtener empresas."""

    def __init__(self, repositorio: RepositorioEmpresa) -> None:
        self._repositorio = repositorio

    async def crear(self, dto: SolicitudCrearEmpresa) -> RespuestaEmpresa:
        """Registra una empresa; lanza `NitDuplicadoError` si el NIT ya existe."""
        existente = await self._repositorio.buscar_por_nit(dto.nit)
        if existente is not None:
            raise NitDuplicadoError()
        empresa = Empresa.crear(
            razon_social=dto.razon_social,
            nit=dto.nit,
            actividad_economica=dto.actividad_economica,
            nivel_riesgo_arl=dto.nivel_riesgo_arl,
            numero_trabajadores=dto.numero_trabajadores,
        )
        guardada = await self._repositorio.guardar(empresa)
        return MapperEmpresa.a_respuesta(guardada)

    async def listar(self) -> list[RespuestaEmpresa]:
        """Lista todas las empresas registradas."""
        empresas = await self._repositorio.listar()
        return [MapperEmpresa.a_respuesta(e) for e in empresas]

    async def obtener(self, id: UUID) -> RespuestaEmpresa:
        """Devuelve una empresa por id; `None` → `EmpresaNoEncontradaError`."""
        empresa = await self._repositorio.buscar_por_id(id)
        if empresa is None:
            raise EmpresaNoEncontradaError()
        return MapperEmpresa.a_respuesta(empresa)
