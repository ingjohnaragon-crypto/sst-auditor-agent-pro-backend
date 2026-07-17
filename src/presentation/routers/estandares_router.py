"""Router del catálogo de estándares mínimos (Res. 0312)."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.respuesta_estandar_minimo import RespuestaEstandarMinimo
from src.application.services.servicio_autoevaluaciones import ServicioAutoevaluaciones
from src.domain.models.estandar_minimo import CicloPHVA
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import (
    obtener_servicio_autoevaluaciones,
)

RESPUESTAS_ERROR_AUTH: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

router = APIRouter(prefix="/estandares-minimos", tags=["Estándares mínimos"])


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaEstandarMinimo],
    responses=RESPUESTAS_ERROR_AUTH,
    summary="Lista el catálogo de estándares mínimos",
)
async def listar_estandares(
    ciclo_phva: Literal["PLANEAR", "HACER", "VERIFICAR", "ACTUAR"] | None = Query(default=None),
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioAutoevaluaciones = Depends(obtener_servicio_autoevaluaciones),
) -> list[RespuestaEstandarMinimo]:
    """Devuelve el catálogo; filtro opcional por ciclo PHVA (valor inválido → 422)."""
    ciclo = CicloPHVA(ciclo_phva) if ciclo_phva is not None else None
    return await servicio.listar_estandares(ciclo)
