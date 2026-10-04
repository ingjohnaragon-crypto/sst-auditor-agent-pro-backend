"""Router de solo lectura del resumen ejecutivo por empresa."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.respuesta_resumen_ejecutivo import RespuestaResumenEjecutivo
from src.application.services.servicio_resumen_ejecutivo import ServicioResumenEjecutivo
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.resumen_ejecutivo import (
    obtener_servicio_resumen_ejecutivo,
)

router = APIRouter(prefix="/empresas", tags=["Empresas"])


@router.get(
    "/{empresa_id}/resumen-ejecutivo",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaResumenEjecutivo,
    responses={
        401: {
            "model": RespuestaError,
            "description": "Token inválido o ausente (TOKEN_INVALIDO)",
        },
        404: {
            "model": RespuestaError,
            "description": "Empresa inexistente (EMPRESA_NO_ENCONTRADA)",
        },
    },
    summary="Resumen ejecutivo de una empresa",
)
async def obtener_resumen_ejecutivo(
    empresa_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioResumenEjecutivo = Depends(obtener_servicio_resumen_ejecutivo),
) -> RespuestaResumenEjecutivo:
    """Cualquier rol autenticado, incluido CONSULTA. No escribe datos."""
    return await servicio.obtener(empresa_id)
