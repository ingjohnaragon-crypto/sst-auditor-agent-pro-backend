"""Integración HTTP de la carga multipart de evidencias."""

from uuid import uuid4

from fastapi import Depends
from httpx import AsyncClient
from src.application.services.servicio_carga_evidencia import ServicioCargaEvidencia
from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_tokens import ServicioTokens
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.config.settings import get_settings
from src.main import app
from src.presentation.dependencies.autenticacion import (
    obtener_repositorio_usuario,
    obtener_servicio_tokens,
)
from src.presentation.dependencies.evidencia import (
    obtener_repositorio_acceso_evidencia,
    obtener_repositorio_evidencia,
    obtener_servicio_carga_evidencia,
    obtener_servicio_descarga_evidencia,
)

from tests.integration.conftest import CatalogoSemilla, UsuariosSemilla
from tests.integration.helpers_auth import bearer, obtener_token

PDF = b"%PDF-1.4 evidencia"


def _override_almacen(almacen: AlmacenMemoria, *, r2_configurado: bool = True) -> None:
    def override_carga(
        repositorio: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
    ) -> ServicioCargaEvidencia:
        return ServicioCargaEvidencia(
            repositorio=repositorio,
            almacen=almacen,
            r2_configurado=r2_configurado,
        )

    def override_descarga(
        repositorio_evidencia: RepositorioEvidencia = Depends(obtener_repositorio_evidencia),
        repositorio_usuario: RepositorioUsuario = Depends(obtener_repositorio_usuario),
        repositorio_acceso: RepositorioAccesoEvidencia = Depends(
            obtener_repositorio_acceso_evidencia
        ),
        servicio_tokens: ServicioTokens = Depends(obtener_servicio_tokens),
    ) -> ServicioDescargaEvidencia:
        settings = get_settings()
        return ServicioDescargaEvidencia(
            repositorio_evidencia=repositorio_evidencia,
            repositorio_usuario=repositorio_usuario,
            repositorio_acceso=repositorio_acceso,
            servicio_tokens=servicio_tokens,
            almacen=almacen,
            segundos_expiracion=settings.descarga_segundos_expiracion,
            prefijo_api=settings.api_prefix,
        )

    app.dependency_overrides[obtener_servicio_carga_evidencia] = override_carga
    app.dependency_overrides[obtener_servicio_descarga_evidencia] = override_descarga


def _limpiar_overrides() -> None:
    app.dependency_overrides.pop(obtener_servicio_carga_evidencia, None)
    app.dependency_overrides.pop(obtener_servicio_descarga_evidencia, None)


async def _calificacion_id(
    cliente: AsyncClient,
    headers: dict[str, str],
    catalogo: CatalogoSemilla,
) -> tuple[str, str]:
    empresa = await cliente.post(
        "/api/v1/empresas",
        headers=headers,
        json={
            "razon_social": "Empresa Carga SA",
            "nit": f"900{uuid4().int % 10_000_000:07d}-9",
            "actividad_economica": "Consultoría SST",
            "nivel_riesgo_arl": "II",
            "numero_trabajadores": 12,
        },
    )
    assert empresa.status_code == 201
    empresa_id = str(empresa.json()["id"])
    auto = await cliente.post(
        "/api/v1/autoevaluaciones",
        headers=headers,
        json={"empresa_id": empresa_id, "fecha": "2026-09-01"},
    )
    assert auto.status_code == 201
    cal = await cliente.put(
        f"/api/v1/autoevaluaciones/{auto.json()['id']}/calificaciones/{catalogo.estandar_ids[0]}",
        headers=headers,
        json={"resultado": "CUMPLE"},
    )
    assert cal.status_code == 200
    return str(cal.json()["id"]), empresa_id


async def test_should_subir_y_descargar_el_mismo_archivo(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_almacen(almacen)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        calificacion_id, empresa_id = await _calificacion_id(
            cliente_async, headers, catalogo_semilla
        )
        alta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert alta.status_code == 201
        assert alta.json()["tamano_bytes"] == len(PDF)
        clave = alta.json()["ruta_almacenamiento"]
        assert clave.startswith(f"evidencias/{empresa_id}/")
        assert almacen.objetos[clave] == PDF

        enlace = await cliente_async.post(
            f"/api/v1/evidencias/{alta.json()['id']}/enlace-descarga",
            headers=headers,
        )
        assert enlace.status_code == 200
        canje = await cliente_async.get(enlace.json()["url"])
        assert canje.status_code == 200
        assert canje.content == PDF
    finally:
        _limpiar_overrides()


async def test_should_responder_403_when_consulta_sube(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_almacen(almacen)
    try:
        token_admin = await obtener_token(cliente_async, usuarios_semilla)
        calificacion_id, _ = await _calificacion_id(
            cliente_async, bearer(token_admin), catalogo_semilla
        )
        token_consulta = await obtener_token(
            cliente_async, usuarios_semilla, correo=usuarios_semilla.correo_consulta
        )
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=bearer(token_consulta),
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"
    finally:
        _limpiar_overrides()


async def test_should_responder_404_when_calificacion_no_existe(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
) -> None:
    _override_almacen(AlmacenMemoria())
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{uuid4()}/archivo",
            headers=bearer(token),
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 404
        assert respuesta.json()["codigo"] == "CALIFICACION_NO_ENCONTRADA"
    finally:
        _limpiar_overrides()


async def test_should_responder_422_y_no_dejar_objeto(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_almacen(almacen)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        calificacion_id, _ = await _calificacion_id(cliente_async, headers, catalogo_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=headers,
            files={"archivo": ("acta.pdf", b"\x89PNG\r\n\x1a\n", "application/pdf")},
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["codigo"] == "EVIDENCIA_INVALIDA"
        assert almacen.objetos == {}
    finally:
        _limpiar_overrides()


async def test_should_responder_503_when_r2_no_configurado(
    cliente_async: AsyncClient,
    usuarios_semilla: UsuariosSemilla,
    catalogo_semilla: CatalogoSemilla,
) -> None:
    almacen = AlmacenMemoria()
    _override_almacen(almacen, r2_configurado=False)
    try:
        token = await obtener_token(cliente_async, usuarios_semilla)
        headers = bearer(token)
        calificacion_id, _ = await _calificacion_id(cliente_async, headers, catalogo_semilla)
        respuesta = await cliente_async.post(
            f"/api/v1/calificaciones-estandar/{calificacion_id}/archivo",
            headers=headers,
            files={"archivo": ("acta.pdf", PDF, "application/pdf")},
        )
        assert respuesta.status_code == 503
        assert respuesta.json()["codigo"] == "ALMACENAMIENTO_NO_CONFIGURADO"
        assert almacen.objetos == {}
    finally:
        _limpiar_overrides()
