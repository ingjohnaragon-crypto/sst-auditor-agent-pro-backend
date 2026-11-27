"""Router de documentos de empresa del catálogo PHVA."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import status as http_status
from fastapi.responses import Response

from src.application.dto.respuesta_documento_empresa import (
    RespuestaDocumentoEmpresa,
    SolicitudMarcarDocumento,
)
from src.application.dto.respuesta_error import RespuestaError
from src.application.services.servicio_carga_evidencia import TAMANO_BLOQUE, leer_con_tope
from src.application.services.servicio_documentos_empresa import ServicioDocumentosEmpresa
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.exceptions.documento_empresa import DocumentoInvalidoError
from src.domain.exceptions.evidencia import EvidenciaInvalidaError
from src.domain.models.documento_empresa import EstadoDocumentoEmpresa
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.autoevaluacion import requerir_rol_escritor
from src.presentation.dependencies.documento_empresa import (
    obtener_servicio_documentos_empresa,
)

RESPUESTAS_ERROR_COMUNES: dict[int | str, dict[str, object]] = {
    401: {
        "model": RespuestaError,
        "description": "Token inválido o ausente (TOKEN_INVALIDO)",
    },
    404: {
        "model": RespuestaError,
        "description": "Empresa, tipo o documento no encontrado",
    },
    422: {"model": RespuestaError, "description": "Datos de entrada inválidos"},
}

RESPUESTAS_ESCRITURA: dict[int | str, dict[str, object]] = {
    **RESPUESTAS_ERROR_COMUNES,
    403: {
        "model": RespuestaError,
        "description": "Rol CONSULTA sin permiso de escritura (ACCESO_DENEGADO)",
    },
    409: {
        "model": RespuestaError,
        "description": "Transición de estado no permitida (CONFLICTO_ESTADO_DOCUMENTO)",
    },
    503: {
        "model": RespuestaError,
        "description": "Almacenamiento R2 no configurado (ALMACENAMIENTO_NO_CONFIGURADO)",
    },
}

router = APIRouter(
    prefix="/empresas/{empresa_id}/documentos",
    tags=["Documentos empresa PHVA"],
)


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaDocumentoEmpresa],
    responses=RESPUESTAS_ERROR_COMUNES,
    summary="Lista el estado documental PHVA de una empresa",
)
async def listar_documentos_empresa(
    empresa_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioDocumentosEmpresa = Depends(obtener_servicio_documentos_empresa),
) -> list[RespuestaDocumentoEmpresa]:
    """Devuelve un ítem por tipo; sin fila se presenta como PENDIENTE."""
    return await servicio.listar_por_empresa(empresa_id)


@router.post(
    "/{tipo_id}/archivo",
    status_code=http_status.HTTP_201_CREATED,
    response_model=RespuestaDocumentoEmpresa,
    responses=RESPUESTAS_ESCRITURA,
    summary="Carga o reemplaza el archivo de un tipo documental",
)
async def cargar_documento(
    empresa_id: UUID,
    tipo_id: UUID,
    archivo: UploadFile = File(...),
    escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioDocumentosEmpresa = Depends(obtener_servicio_documentos_empresa),
) -> RespuestaDocumentoEmpresa:
    """Guarda el binario en R2 y deja el documento en CARGADO."""
    if escritor.id is None:
        raise TokenInvalidoException()
    try:
        contenido = leer_con_tope(iter(lambda: archivo.file.read(TAMANO_BLOQUE), b""))
    except EvidenciaInvalidaError as exc:
        raise DocumentoInvalidoError(str(exc)) from exc
    return await servicio.cargar(
        empresa_id,
        tipo_id,
        archivo.filename or "",
        archivo.content_type or "",
        contenido,
        escritor.id,
    )


@router.get(
    "/{tipo_id}/archivo",
    status_code=http_status.HTTP_200_OK,
    responses={
        **RESPUESTAS_ERROR_COMUNES,
        404: {
            "model": RespuestaError,
            "description": "Documento o objeto no disponible",
        },
    },
    summary="Descarga el binario del documento por tipo",
    response_class=Response,
)
async def descargar_documento(
    empresa_id: UUID,
    tipo_id: UUID,
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioDocumentosEmpresa = Depends(obtener_servicio_documentos_empresa),
) -> Response:
    """Transmite con sesión Bearer; no expone URL de R2 ni clave_objeto."""
    descarga = await servicio.descargar(empresa_id, tipo_id)
    return Response(
        content=descarga.contenido,
        media_type=descarga.tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{descarga.nombre_original}"'},
    )


@router.patch(
    "/{tipo_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=RespuestaDocumentoEmpresa,
    responses=RESPUESTAS_ESCRITURA,
    summary="Marca el documento como REVISADO",
)
async def marcar_documento(
    empresa_id: UUID,
    tipo_id: UUID,
    cuerpo: SolicitudMarcarDocumento,
    _escritor: Usuario = Depends(requerir_rol_escritor),
    servicio: ServicioDocumentosEmpresa = Depends(obtener_servicio_documentos_empresa),
) -> RespuestaDocumentoEmpresa:
    """Solo acepta estado REVISADO desde CARGADO."""
    if cuerpo.estado.strip().upper() != EstadoDocumentoEmpresa.REVISADO.value:
        raise DocumentoInvalidoError("Solo se admite el estado REVISADO en este endpoint")
    return await servicio.marcar_revisado(empresa_id, tipo_id)
