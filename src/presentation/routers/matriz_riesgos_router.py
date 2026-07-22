"""Router de la matriz de riesgos GTC 45."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi import status as http_status

from src.application.dto.matriz_riesgo import (
    RespuestaControlRiesgo,
    RespuestaEvaluacionRiesgo,
    RespuestaMatrizRiesgos,
    RespuestaPeligro,
    RespuestaProcesoActividad,
    SolicitudActualizarControl,
    SolicitudActualizarPeligro,
    SolicitudActualizarProcesoActividad,
    SolicitudCrearControl,
    SolicitudCrearPeligro,
    SolicitudCrearProcesoActividad,
    SolicitudUpsertEvaluacion,
)
from src.application.dto.respuesta_error import RespuestaError
from src.application.services.servicio_matriz_riesgos import ServicioMatrizRiesgos
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import requerir_rol_escritor
from src.presentation.dependencies.matriz_riesgo import obtener_servicio_matriz_riesgos

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    403: {
        "model": RespuestaError,
        "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
    },
    404: {"model": RespuestaError, "description": "Recurso no encontrado"},
    422: {"model": RespuestaError, "description": "Datos inválidos / VALOR_GTC_INVALIDO"},
}

router = APIRouter(tags=["Matriz de riesgos GTC 45"])


@router.get(
    "/empresas/{empresa_id}/matriz-riesgos",
    response_model=RespuestaMatrizRiesgos,
    responses=RESPUESTAS_ERROR_COMUNES,
    summary="Vista agregada de la matriz de riesgos",
)
async def obtener_matriz(
    empresa_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaMatrizRiesgos:
    return await servicio.obtener_matriz(empresa_id)


@router.get(
    "/empresas/{empresa_id}/procesos-actividades",
    response_model=list[RespuestaProcesoActividad],
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def listar_procesos(
    empresa_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> list[RespuestaProcesoActividad]:
    return await servicio.listar_procesos(empresa_id)


@router.post(
    "/empresas/{empresa_id}/procesos-actividades",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaProcesoActividad,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def crear_proceso(
    empresa_id: UUID,
    solicitud: SolicitudCrearProcesoActividad,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaProcesoActividad:
    return await servicio.crear_proceso(empresa_id, solicitud)


@router.get(
    "/procesos-actividades/{proceso_id}",
    response_model=RespuestaProcesoActividad,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def obtener_proceso(
    proceso_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaProcesoActividad:
    return await servicio.obtener_proceso(proceso_id)


@router.patch(
    "/procesos-actividades/{proceso_id}",
    response_model=RespuestaProcesoActividad,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def actualizar_proceso(
    proceso_id: UUID,
    solicitud: SolicitudActualizarProcesoActividad,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaProcesoActividad:
    return await servicio.actualizar_proceso(proceso_id, solicitud)


@router.delete(
    "/procesos-actividades/{proceso_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def eliminar_proceso(
    proceso_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> Response:
    await servicio.eliminar_proceso(proceso_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.get(
    "/procesos-actividades/{proceso_id}/peligros",
    response_model=list[RespuestaPeligro],
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def listar_peligros(
    proceso_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> list[RespuestaPeligro]:
    return await servicio.listar_peligros(proceso_id)


@router.post(
    "/procesos-actividades/{proceso_id}/peligros",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaPeligro,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def crear_peligro(
    proceso_id: UUID,
    solicitud: SolicitudCrearPeligro,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaPeligro:
    return await servicio.crear_peligro(proceso_id, solicitud)


@router.get(
    "/peligros/{peligro_id}",
    response_model=RespuestaPeligro,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def obtener_peligro(
    peligro_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaPeligro:
    return await servicio.obtener_peligro(peligro_id)


@router.patch(
    "/peligros/{peligro_id}",
    response_model=RespuestaPeligro,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def actualizar_peligro(
    peligro_id: UUID,
    solicitud: SolicitudActualizarPeligro,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaPeligro:
    return await servicio.actualizar_peligro(peligro_id, solicitud)


@router.delete(
    "/peligros/{peligro_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def eliminar_peligro(
    peligro_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> Response:
    await servicio.eliminar_peligro(peligro_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.get(
    "/peligros/{peligro_id}/evaluacion",
    response_model=RespuestaEvaluacionRiesgo,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def obtener_evaluacion(
    peligro_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaEvaluacionRiesgo:
    return await servicio.obtener_evaluacion(peligro_id)


@router.put(
    "/peligros/{peligro_id}/evaluacion",
    response_model=RespuestaEvaluacionRiesgo,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def upsert_evaluacion(
    peligro_id: UUID,
    solicitud: SolicitudUpsertEvaluacion,
    response: Response,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaEvaluacionRiesgo:
    resultado, creado = await servicio.upsert_evaluacion(peligro_id, solicitud)
    response.status_code = http_status.HTTP_201_CREATED if creado else http_status.HTTP_200_OK
    return resultado


@router.get(
    "/evaluaciones-riesgo/{evaluacion_id}/controles",
    response_model=list[RespuestaControlRiesgo],
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def listar_controles(
    evaluacion_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> list[RespuestaControlRiesgo]:
    return await servicio.listar_controles(evaluacion_id)


@router.post(
    "/evaluaciones-riesgo/{evaluacion_id}/controles",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaControlRiesgo,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def crear_control(
    evaluacion_id: UUID,
    solicitud: SolicitudCrearControl,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaControlRiesgo:
    return await servicio.crear_control(evaluacion_id, solicitud)


@router.patch(
    "/controles-riesgo/{control_id}",
    response_model=RespuestaControlRiesgo,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def actualizar_control(
    control_id: UUID,
    solicitud: SolicitudActualizarControl,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> RespuestaControlRiesgo:
    return await servicio.actualizar_control(control_id, solicitud)


@router.delete(
    "/controles-riesgo/{control_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses=RESPUESTAS_ERROR_COMUNES,
)
async def eliminar_control(
    control_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioMatrizRiesgos = Depends(obtener_servicio_matriz_riesgos),
) -> Response:
    await servicio.eliminar_control(control_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
