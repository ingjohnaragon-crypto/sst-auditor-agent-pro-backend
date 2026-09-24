"""Router de metadatos de evidencias de soporte."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http_status
from fastapi.responses import FileResponse

from src.application.dto.respuesta_enlace_descarga import RespuestaEnlaceDescarga
from src.application.dto.respuesta_error import RespuestaError
from src.application.dto.respuesta_evidencia import RespuestaEvidencia
from src.application.dto.solicitud_registrar_evidencia import SolicitudRegistrarEvidencia
from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.application.services.servicio_evidencias import ServicioEvidencias
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import requerir_rol_escritor
from src.presentation.dependencies.evidencia import (
    obtener_servicio_descarga_evidencia,
    obtener_servicio_evidencias,
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

router_por_calificacion = APIRouter(
    prefix="/calificaciones-estandar",
    tags=["Evidencias"],
)
router = APIRouter(prefix="/evidencias", tags=["Evidencias"])
router_descargas = APIRouter(prefix="/descargas", tags=["Evidencias"])


@router_por_calificacion.post(
    "/{calificacion_id}/evidencias",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaEvidencia,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Calificación inexistente (CALIFICACION_NO_ENCONTRADA)",
        },
    },
    summary="Registra metadatos de un documento de soporte",
)
async def registrar_evidencia(
    calificacion_id: UUID,
    solicitud: SolicitudRegistrarEvidencia,
    escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioEvidencias = Depends(obtener_servicio_evidencias),
) -> RespuestaEvidencia:
    """Persiste metadatos. El binario no viaja en esta petición."""
    if escritor.id is None:
        raise TokenInvalidoException()
    return await servicio.registrar(calificacion_id, solicitud, escritor.id)


@router_por_calificacion.get(
    "/{calificacion_id}/evidencias",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaEvidencia],
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Calificación inexistente (CALIFICACION_NO_ENCONTRADA)",
        },
    },
    summary="Lista evidencias activas de una calificación",
)
async def listar_evidencias(
    calificacion_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioEvidencias = Depends(obtener_servicio_evidencias),
) -> list[RespuestaEvidencia]:
    """Solo filas con `activo=true`."""
    return await servicio.listar_activas(calificacion_id)


@router.delete(
    "/{id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Evidencia inexistente (EVIDENCIA_NO_ENCONTRADA)",
        },
        409: {
            "model": RespuestaError,
            "description": "La evidencia ya fue dada de baja (EVIDENCIA_YA_INACTIVA)",
        },
    },
    summary="Da de baja lógica una evidencia",
)
async def dar_de_baja_evidencia(
    id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioEvidencias = Depends(obtener_servicio_evidencias),
) -> Response:
    """Marca `activo=false`. No borra la fila."""
    await servicio.dar_de_baja(id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{id}/enlace-descarga",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaEnlaceDescarga,
    responses={
        **RESPUESTAS_ESCRITURA,
        404: {
            "model": RespuestaError,
            "description": "Evidencia inexistente o inactiva (EVIDENCIA_NO_ENCONTRADA)",
        },
    },
    summary="Emite un enlace temporal de descarga",
)
async def emitir_enlace_descarga(
    id: UUID,
    escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioDescargaEvidencia = Depends(obtener_servicio_descarga_evidencia),
) -> RespuestaEnlaceDescarga:
    """Devuelve una URL relativa con JWT `tipo=descarga`. No incluye el binario."""
    return await servicio.emitir_enlace(id, escritor)


@router_descargas.get(
    "/evidencias",
    status_code=http_status.HTTP_200_OK,
    responses={
        401: {
            "model": RespuestaError,
            "description": "Token de descarga inválido o vencido",
        },
        403: {
            "model": RespuestaError,
            "description": "Rol o usuario sin permiso (ACCESO_DENEGADO)",
        },
        404: {
            "model": RespuestaError,
            "description": "EVIDENCIA_NO_ENCONTRADA o ARCHIVO_NO_DISPONIBLE",
        },
    },
    summary="Canjea un enlace de descarga",
)
async def canjear_descarga(
    token: str = Query(...),
    servicio: ServicioDescargaEvidencia = Depends(obtener_servicio_descarga_evidencia),
) -> FileResponse:
    """Sirve el archivo si el token y la ruta contenida lo permiten."""
    archivo = await servicio.canjear(token)
    return FileResponse(
        path=archivo.ruta,
        media_type=archivo.tipo_mime,
        filename=archivo.nombre_archivo,
    )
