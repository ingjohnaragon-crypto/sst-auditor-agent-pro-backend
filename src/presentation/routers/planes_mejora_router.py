"""Router del plan de mejora y de sus actividades de cronograma."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi import status as http_status

from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.respuesta_plan_mejora import RespuestaPlanMejora
from src.application.dto.solicitud_plan_mejora import (
    SolicitudAbrirPlanMejora,
    SolicitudActividadCronograma,
)
from src.application.services.servicio_planes_mejora import ServicioPlanesMejora
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import (
    obtener_servicio_planes_mejora,
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

router_por_autoevaluacion = APIRouter(prefix="/autoevaluaciones", tags=["Planes de mejora"])
router = APIRouter(prefix="/planes-mejora", tags=["Planes de mejora"])


@router_por_autoevaluacion.post(
    "/{autoevaluacion_id}/plan-mejora",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaPlanMejora,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Autoevaluación inexistente (AUTOEVALUACION_NO_ENCONTRADA)",
        },
        409: {
            "model": RespuestaError,
            "description": (
                "AUTOEVALUACION_EN_BORRADOR / PLAN_MEJORA_NO_REQUERIDO / PLAN_MEJORA_YA_EXISTE"
            ),
        },
    },
    summary="Abre el plan de mejora de una autoevaluación finalizada",
)
async def abrir_plan(
    autoevaluacion_id: UUID,
    solicitud: SolicitudAbrirPlanMejora,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> RespuestaPlanMejora:
    """Crea el plan. La empresa y el vínculo salen de la autoevaluación."""
    return await servicio.abrir(autoevaluacion_id, solicitud)


@router_por_autoevaluacion.get(
    "/{autoevaluacion_id}/plan-mejora",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaPlanMejora,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "La autoevaluación no tiene plan (PLAN_MEJORA_NO_ENCONTRADO)",
        },
    },
    summary="Lee el plan de mejora de una autoevaluación",
)
async def obtener_plan_por_autoevaluacion(
    autoevaluacion_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> RespuestaPlanMejora:
    """Cualquier rol autenticado, incluido CONSULTA, puede leer."""
    return await servicio.obtener_por_autoevaluacion(autoevaluacion_id)


@router.get(
    "/{plan_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaPlanMejora,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Plan inexistente (PLAN_MEJORA_NO_ENCONTRADO)",
        },
    },
    summary="Lee un plan de mejora por id",
)
async def obtener_plan(
    plan_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> RespuestaPlanMejora:
    """Detalle del plan y de sus actividades."""
    return await servicio.obtener(plan_id)


@router.delete(
    "/{plan_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Plan inexistente (PLAN_MEJORA_NO_ENCONTRADO)",
        },
    },
    summary="Elimina el plan de mejora",
)
async def eliminar_plan(
    plan_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> Response:
    """El CASCADE de la base elimina actividades y meses."""
    await servicio.eliminar(plan_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{plan_id}/actividades",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaPlanMejora,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Plan inexistente (PLAN_MEJORA_NO_ENCONTRADO)",
        },
    },
    summary="Agrega una actividad al cronograma",
)
async def agregar_actividad(
    plan_id: UUID,
    solicitud: SolicitudActividadCronograma,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> RespuestaPlanMejora:
    """Devuelve el plan completo, con la actividad nueva."""
    return await servicio.agregar_actividad(plan_id, solicitud)


@router.put(
    "/{plan_id}/actividades/{actividad_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaPlanMejora,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "PLAN_MEJORA_NO_ENCONTRADO / ACTIVIDAD_NO_ENCONTRADA",
        },
    },
    summary="Actualiza una actividad del cronograma",
)
async def actualizar_actividad(
    plan_id: UUID,
    actividad_id: UUID,
    solicitud: SolicitudActividadCronograma,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> RespuestaPlanMejora:
    """Reemplaza textos y meses. El id de la actividad no cambia."""
    return await servicio.actualizar_actividad(plan_id, actividad_id, solicitud)


@router.delete(
    "/{plan_id}/actividades/{actividad_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "PLAN_MEJORA_NO_ENCONTRADO / ACTIVIDAD_NO_ENCONTRADA",
        },
    },
    summary="Quita una actividad del cronograma",
)
async def quitar_actividad(
    plan_id: UUID,
    actividad_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioPlanesMejora = Depends(obtener_servicio_planes_mejora),
) -> Response:
    """Persiste el plan sin esa actividad."""
    await servicio.quitar_actividad(plan_id, actividad_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
