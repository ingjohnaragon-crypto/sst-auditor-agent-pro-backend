"""Router del repositorio documental de empresa."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import status as http_status
from fastapi.responses import Response

from src.application.dto.respuesta_archivo_documental import RespuestaArchivoDocumental
from src.application.dto.respuesta_error import RespuestaError
from src.application.services.servicio_archivos_documentales import (
    ServicioArchivosDocumentales,
)
from src.application.services.servicio_carga_evidencia import TAMANO_BLOQUE, leer_con_tope
from src.domain.exceptions.archivo_documental import ArchivoInvalidoError
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.exceptions.evidencia import EvidenciaInvalidaError
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.archivo_documental import (
    obtener_servicio_archivos_documentales,
)
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import requerir_rol_escritor

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    404: {
        "model": RespuestaError,
        "description": "Empresa o archivo no encontrado",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

RESPUESTAS_ESCRITURA: dict[int | str, dict[str, object]] = {
    **RESPUESTAS_ERROR_COMUNES,
    403: {
        "model": RespuestaError,
        "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
    },
    503: {
        "model": RespuestaError,
        "description": "Almacenamiento R2 no configurado (ALMACENAMIENTO_NO_CONFIGURADO)",
    },
}

router = APIRouter(
    prefix="/empresas/{empresa_id}/archivos",
    tags=["Archivos documentales"],
)


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaArchivoDocumental],
    responses=RESPUESTAS_ERROR_COMUNES,
    summary="Lista los archivos documentales de una empresa",
)
async def listar_archivos(
    empresa_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioArchivosDocumentales = Depends(obtener_servicio_archivos_documentales),
) -> list[RespuestaArchivoDocumental]:
    """Cualquier rol autenticado, incluido CONSULTA, puede listar."""
    return await servicio.listar(empresa_id)


@router.post(
    "",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaArchivoDocumental,
    responses=RESPUESTAS_ESCRITURA,
    summary="Sube un archivo documental de la empresa",
)
async def cargar_archivo(
    empresa_id: UUID,
    archivo: UploadFile = File(...),
    escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioArchivosDocumentales = Depends(obtener_servicio_archivos_documentales),
) -> RespuestaArchivoDocumental:
    """Guarda el binario en R2 y los metadatos. El cliente no elige la clave."""
    if escritor.id is None:
        raise TokenInvalidoException()
    try:
        contenido = leer_con_tope(iter(lambda: archivo.file.read(TAMANO_BLOQUE), b""))
    except EvidenciaInvalidaError as exc:
        raise ArchivoInvalidoError(str(exc)) from exc
    return await servicio.cargar(
        empresa_id,
        archivo.filename or "",
        archivo.content_type or "",
        contenido,
        escritor.id,
    )


@router.get(
    "/{archivo_id}",
    status_code=http_status.HTTP_200_OK,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Archivo o objeto no disponible",
        },
    },
    summary="Descarga el binario de un archivo documental",
    response_class=Response,
)
async def descargar_archivo(
    empresa_id: UUID,
    archivo_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioArchivosDocumentales = Depends(obtener_servicio_archivos_documentales),
) -> Response:
    """Transmite el archivo con la sesión Bearer. No expone URL de R2."""
    descarga = await servicio.descargar(empresa_id, archivo_id)
    nombre_seguro = descarga.nombre_original.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=descarga.contenido,
        media_type=descarga.tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre_seguro}"'},
    )


@router.delete(
    "/{archivo_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses=RESPUESTAS_ESCRITURA,
    summary="Elimina un archivo documental y su objeto en R2",
)
async def eliminar_archivo(
    empresa_id: UUID,
    archivo_id: UUID,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioArchivosDocumentales = Depends(obtener_servicio_archivos_documentales),
) -> Response:
    """Borra el objeto del almacén y la fila de metadatos."""
    await servicio.eliminar(empresa_id, archivo_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
