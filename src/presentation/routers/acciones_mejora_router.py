"""Router del borrador de acciones generado desde incumplimientos."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.application.dto.respuesta_accion_mejora import RespuestaAccionMejora
from src.application.dto.respuesta_error import RespuestaError
from src.application.services.servicio_borrador_acciones import ServicioBorradorAcciones
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import (
    obtener_servicio_borrador_acciones,
    requerir_rol_escritor,
)

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
}

RESPUESTAS_ESCRITURA: dict[int | str, dict[str, object]] = {
    **RESPUESTAS_ERROR_COMUNES,
    403: {
        "model": RespuestaError,
        "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
    },
}

router = APIRouter(prefix="/planes-mejora", tags=["Planes de mejora"])


@router.post(
    "/{plan_id}/acciones/borrador",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaAccionMejora],
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": (
                "PLAN_MEJORA_NO_ENCONTRADO / AUTOEVALUACION_NO_ENCONTRADA / ESTANDAR_NO_ENCONTRADO"
            ),
        },
    },
    summary="Genera el borrador de acciones desde los incumplimientos",
)
async def generar_borrador(
    plan_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioBorradorAcciones = Depends(obtener_servicio_borrador_acciones),
) -> list[RespuestaAccionMejora]:
    """Crea una acción por cada NO_CUMPLE que aún no tenga una."""
    return await servicio.generar(plan_id)


@router.get(
    "/{plan_id}/acciones",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaAccionMejora],
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Plan inexistente (PLAN_MEJORA_NO_ENCONTRADO)",
        },
    },
    summary="Lee el borrador de acciones del plan",
)
async def listar_acciones(
    plan_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioBorradorAcciones = Depends(obtener_servicio_borrador_acciones),
) -> list[RespuestaAccionMejora]:
    """No vuelve a generar. CONSULTA puede leer."""
    return await servicio.listar(plan_id)
