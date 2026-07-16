"""Router de autenticación: login, refresh y perfil del usuario autenticado."""

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.respuesta_tokens import RespuestaTokenAcceso, RespuestaTokens
from src.application.dto.respuesta_usuario import RespuestaUsuario
from src.application.dto.solicitud_login import SolicitudLogin
from src.application.dto.solicitud_refresh import SolicitudRefresh
from src.application.mappers.mapper_usuario import MapperUsuario
from src.application.services.servicio_autenticacion import ServicioAutenticacion
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import (
    obtener_servicio_autenticacion,
    obtener_usuario_actual,
)

RESPUESTAS_ERROR_AUTH: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Credenciales o token inválidos (CREDENCIALES_INVALIDAS, "
        "TOKEN_INVALIDO o TOKEN_EXPIRADO)",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaTokens,
    responses=RESPUESTAS_ERROR_AUTH,
    summary="Inicia sesión y emite el par de tokens (acceso + refresco)",
)
async def login(
    solicitud: SolicitudLogin,
    servicio: ServicioAutenticacion = Depends(obtener_servicio_autenticacion),
) -> RespuestaTokens:
    """Valida las credenciales y devuelve los tokens JWT del usuario."""
    return await servicio.iniciar_sesion(solicitud)


@router.post(
    "/refresh",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaTokenAcceso,
    responses=RESPUESTAS_ERROR_AUTH,
    summary="Renueva el token de acceso a partir del token de refresco",
)
async def refresh(
    solicitud: SolicitudRefresh,
    servicio: ServicioAutenticacion = Depends(obtener_servicio_autenticacion),
) -> RespuestaTokenAcceso:
    """Emite un nuevo token de acceso si el token de refresco es válido."""
    return await servicio.refrescar_token(solicitud)


@router.get(
    "/yo",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaUsuario,
    responses=RESPUESTAS_ERROR_AUTH,
    summary="Devuelve el perfil del usuario autenticado",
)
async def yo(
    usuario: Usuario = Depends(obtener_usuario_actual),
) -> RespuestaUsuario:
    """Perfil del usuario del Bearer token — útil para hidratar sesión en el frontend."""
    # Ya validado y cargado por `obtener_usuario_actual`; evita un round-trip extra a BD.
    return MapperUsuario.a_respuesta(usuario)
