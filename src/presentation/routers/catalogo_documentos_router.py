"""Router del catálogo de tipos documentales PHVA."""

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.application.dto.respuesta_documento_empresa import RespuestaTipoDocumentoSst
from src.application.dto.respuesta_error import RespuestaError
from src.application.services.servicio_documentos_empresa import ServicioDocumentosEmpresa
from src.domain.models.usuario import Usuario
from src.presentation.dependencies.autenticacion import obtener_usuario_actual
from src.presentation.dependencies.documento_empresa import (
    obtener_servicio_documentos_empresa,
)

router = APIRouter(prefix="/catalogo-documentos", tags=["Catálogo documental PHVA"])


@router.get(
    "",
    status_code=http_status.HTTP_200_OK,
    response_model=list[RespuestaTipoDocumentoSst],
    responses={
        401: {
            "model": RespuestaError,
            "description": "Token inválido o ausente (TOKEN_INVALIDO)",
        },
    },
    summary="Lista los tipos de documento del ciclo PHVA",
)
async def listar_catalogo_documentos(
    _usuario: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioDocumentosEmpresa = Depends(obtener_servicio_documentos_empresa),
) -> list[RespuestaTipoDocumentoSst]:
    """Incluye `estandares_ids` cuando hay vínculo con Res. 0312."""
    return await servicio.listar_catalogo()
