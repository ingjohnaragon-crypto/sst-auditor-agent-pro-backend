"""Router de empresas — CRUD mínimo de soporte para autoevaluación."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.application.dto.respuesta_empresa import RespuestaEmpresa
from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.solicitud_crear_empresa import SolicitudCrearEmpresa
from src.application.services.servicio_empresas import ServicioEmpresas
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import (
    obtener_servicio_empresas,
    requerir_rol_escritor,
)

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

router = APIRouter(prefix="/empresas", tags=["Empresas"])


@router.post(
    "",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaEmpresa,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        403: {
            "model": RespuestaError,
            "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
        },
        409: {
            "model": RespuestaError,
            "description": "NIT ya registrado (NIT_DUPLICADO)",
        },
    },
    summary="Registra una empresa",
)
async def crear_empresa(
    solicitud: SolicitudCrearEmpresa,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioEmpresas = Depends(obtener_servicio_empresas),
) -> RespuestaEmpresa:
    """Crea una empresa; exige rol ADMINISTRADOR o AUDITOR_SST."""
    return await servicio.crear(solicitud)


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaEmpresa],
    responses=RESPUESTAS_ERROR_COMUNES,
    summary="Lista las empresas registradas",
)
async def listar_empresas(
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioEmpresas = Depends(obtener_servicio_empresas),
) -> list[RespuestaEmpresa]:
    """Lista todas las empresas; cualquier rol autenticado."""
    return await servicio.listar()


@router.get(
    "/{id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaEmpresa,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Empresa inexistente (EMPRESA_NO_ENCONTRADA)",
        },
    },
    summary="Obtiene una empresa por id",
)
async def obtener_empresa(
    id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioEmpresas = Depends(obtener_servicio_empresas),
) -> RespuestaEmpresa:
    """Detalle de una empresa; cualquier rol autenticado."""
    return await servicio.obtener(id)
