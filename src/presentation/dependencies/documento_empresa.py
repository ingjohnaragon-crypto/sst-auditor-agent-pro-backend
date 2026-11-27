"""Dependencias FastAPI del catálogo documental PHVA."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.servicio_carga_evidencia import AlmacenEvidencias
from src.application.services.servicio_documentos_empresa import ServicioDocumentosEmpresa
from src.domain.repositories.repositorio_documento_empresa import (
    RepositorioDocumentoEmpresa,
)
from src.domain.repositories.repositorio_tipo_documento_sst import (
    RepositorioTipoDocumentoSst,
)
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.sesion import obtener_sesion
from src.infrastructure.repositories.repositorio_documento_empresa_sqlalchemy import (
    RepositorioDocumentoEmpresaSQLAlchemy,
)
from src.infrastructure.repositories.repositorio_tipo_documento_sst_sqlalchemy import (
    RepositorioTipoDocumentoSstSQLAlchemy,
)
from src.presentation.dependencies.archivo_documental import obtener_almacen_archivos
from src.presentation.dependencies.autenticacion import obtener_repositorio_usuario


def obtener_repositorio_tipo_documento(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioTipoDocumentoSst:
    """Ensambla el repositorio del catálogo de tipos."""
    return RepositorioTipoDocumentoSstSQLAlchemy(sesion)


def obtener_repositorio_documento_empresa(
    sesion: AsyncSession = Depends(obtener_sesion),
) -> RepositorioDocumentoEmpresa:
    """Ensambla el repositorio de documentos de empresa."""
    return RepositorioDocumentoEmpresaSQLAlchemy(sesion)


def obtener_servicio_documentos_empresa(
    repositorio_documento: RepositorioDocumentoEmpresa = Depends(
        obtener_repositorio_documento_empresa
    ),
    repositorio_tipo: RepositorioTipoDocumentoSst = Depends(obtener_repositorio_tipo_documento),
    almacen: AlmacenEvidencias = Depends(obtener_almacen_archivos),
    repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
) -> ServicioDocumentosEmpresa:
    """Caso de uso documental PHVA con el almacén configurado."""
    settings = get_settings()
    return ServicioDocumentosEmpresa(
        repositorio_documento=repositorio_documento,
        repositorio_tipo=repositorio_tipo,
        almacen=almacen,
        repositorio_usuario=repositorio_usuario,
        r2_configurado=settings.r2_configurado,
    )
