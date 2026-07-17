"""Router de autoevaluaciones de estándares mínimos (Res. 0312)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from src.application.dto.respuesta_autoevaluacion import RespuestaAutoevaluacion
from src.application.dto.respuesta_calificacion_estandar import (
    RespuestaCalificacionEstandar,
)
from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.solicitud_calificar_estandar import SolicitudCalificarEstandar
from src.application.dto.solicitud_crear_autoevaluacion import (
    SolicitudCrearAutoevaluacion,
)
from src.application.services.servicio_autoevaluaciones import ServicioAutoevaluaciones
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import (
    obtener_servicio_autoevaluaciones,
    requerir_rol_escritor,
)

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

RESPUESTAS_ESCRITURA: dict[int | str, dict[str, object]] = {
    **RESPUESTAS_ERROR_COMUNES,
    403: {
        "model": RespuestaError,
        "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
    },
}

router = APIRouter(prefix="/autoevaluaciones", tags=["Autoevaluaciones"])


@router.post(
    "",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaAutoevaluacion,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Empresa inexistente (EMPRESA_NO_ENCONTRADA)",
        },
    },
    summary="Inicia una autoevaluación",
)
async def crear_autoevaluacion(
    solicitud: SolicitudCrearAutoevaluacion,
    escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> RespuestaAutoevaluacion:
    """Crea una autoevaluación; `usuario_id` se toma del Bearer token."""
    if escritor.id is None:
        raise TokenInvalidoException()
    return await servicio.crear(solicitud, escritor.id)


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaAutoevaluacion],
    responses=RESPUESTAS_ERROR_COMUNES,
    summary="Lista el histórico de autoevaluaciones de una empresa",
)
async def listar_autoevaluaciones(
    empresa_id: UUID = Query(...),
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> list[RespuestaAutoevaluacion]:
    """Histórico ordenado por fecha desc; sin calificaciones embebidas."""
    return await servicio.listar_por_empresa(empresa_id)


@router.get(
    "/{id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaAutoevaluacion,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Autoevaluación inexistente (AUTOEVALUACION_NO_ENCONTRADA)",
        },
    },
    summary="Obtiene el detalle de una autoevaluación",
)
async def obtener_autoevaluacion(
    id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> RespuestaAutoevaluacion:
    """Detalle con calificaciones embebidas."""
    return await servicio.obtener(id)


@router.put(
    "/{id}/calificaciones/{estandar_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaCalificacionEstandar,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Autoevaluación o estándar inexistente "
            "(AUTOEVALUACION_NO_ENCONTRADA / ESTANDAR_NO_ENCONTRADO)",
        },
        409: {
            "model": RespuestaError,
            "description": "Autoevaluación ya finalizada (AUTOEVALUACION_FINALIZADA)",
        },
    },
    summary="Califica (o recalifica) un estándar mínimo",
)
async def calificar_estandar(
    id: UUID,
    estandar_id: UUID,
    solicitud: SolicitudCalificarEstandar,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> RespuestaCalificacionEstandar:
    """Upsert idempotente; el puntaje se deriva en dominio."""
    return await servicio.calificar(id, estandar_id, solicitud)


@router.post(
    "/{id}/finalizar",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaAutoevaluacion,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Autoevaluación inexistente (AUTOEVALUACION_NO_ENCONTRADA)",
        },
        409: {
            "model": RespuestaError,
            "description": "Incompleta o ya finalizada "
            "(AUTOEVALUACION_INCOMPLETA / AUTOEVALUACION_FINALIZADA)",
        },
    },
    summary="Finaliza una autoevaluación y calcula el puntaje total",
)
async def finalizar_autoevaluacion(
    id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> RespuestaAutoevaluacion:
    """Exige todos los ítems del catálogo; fija `puntaje_total` y plan de mejora."""
    return await servicio.finalizar(id)
