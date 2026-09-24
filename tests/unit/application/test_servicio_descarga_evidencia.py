"""Pruebas de emisión y canje de enlaces de descarga."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.application.services.servicio_descarga_evidencia import ServicioDescargaEvidencia
from src.domain.exceptions.autenticacion import TokenExpiradoException, TokenInvalidoException
from src.domain.exceptions.autoevaluacion import AccesoDenegadoError
from src.domain.exceptions.evidencia import ArchivoNoDisponibleError, EvidenciaNoEncontradaError
from src.domain.models.acceso_evidencia import ResultadoAccesoEvidencia
from src.domain.models.evidencia import Evidencia
from src.domain.models.usuario import RolUsuario, Usuario
from src.domain.repositories.servicio_tokens import TIPO_TOKEN_DESCARGA


def _usuario(rol: RolUsuario = RolUsuario.AUDITOR_SST, *, activo: bool = True) -> Usuario:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="hash",
        rol=rol,
    )
    usuario.id = uuid4()
    usuario.activo = activo
    return usuario


def _evidencia(*, activo: bool = True) -> Evidencia:
    evidencia = Evidencia.crear(
        calificacion_estandar_id=uuid4(),
        usuario_id=uuid4(),
        nombre_archivo="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=128,
        ruta_almacenamiento="empresas/acta.pdf",
    )
    evidencia.id = uuid4()
    evidencia.activo = activo
    return evidencia


def _servicio(
    evidencia: Evidencia | None,
    usuario: Usuario | None,
    *,
    raiz: Path | None = None,
) -> tuple[ServicioDescargaEvidencia, AsyncMock, MagicMock]:
    evidencias = AsyncMock()
    evidencias.buscar_por_id.return_value = evidencia
    usuarios = AsyncMock()
    usuarios.buscar_por_id.return_value = usuario
    accesos = AsyncMock()
    tokens = MagicMock()
    tokens.emitir_token_descarga.return_value = "jwt-descarga"
    servicio = ServicioDescargaEvidencia(
        repositorio_evidencia=evidencias,
        repositorio_usuario=usuarios,
        repositorio_acceso=accesos,
        servicio_tokens=tokens,
        segundos_expiracion=300,
        prefijo_api="/api/v1",
        raiz_almacenamiento=raiz,
    )
    return servicio, accesos, tokens


@pytest.mark.asyncio
async def test_should_emitir_enlace_when_escritor_y_evidencia_activa() -> None:
    evidencia = _evidencia()
    usuario = _usuario()
    servicio, _accesos, tokens = _servicio(evidencia, usuario)

    respuesta = await servicio.emitir_enlace(evidencia.id, usuario)  # type: ignore[arg-type]

    assert respuesta.expira_en_segundos == 300
    assert respuesta.url.startswith("/api/v1/descargas/evidencias?token=")
    tokens.emitir_token_descarga.assert_called_once()


@pytest.mark.asyncio
async def test_should_rechazar_consulta_when_pide_enlace() -> None:
    evidencia = _evidencia()
    servicio, _accesos, tokens = _servicio(evidencia, _usuario(RolUsuario.CONSULTA))

    with pytest.raises(AccesoDenegadoError):
        await servicio.emitir_enlace(evidencia.id, _usuario(RolUsuario.CONSULTA))  # type: ignore[arg-type]
    tokens.emitir_token_descarga.assert_not_called()


@pytest.mark.asyncio
async def test_should_responder_404_when_evidencia_inactiva_al_emitir() -> None:
    evidencia = _evidencia(activo=False)
    servicio, _accesos, tokens = _servicio(evidencia, _usuario())

    with pytest.raises(EvidenciaNoEncontradaError):
        await servicio.emitir_enlace(evidencia.id, _usuario())  # type: ignore[arg-type]
    tokens.emitir_token_descarga.assert_not_called()


@pytest.mark.asyncio
async def test_should_rechazar_token_de_sesion_when_canjear() -> None:
    servicio, accesos, tokens = _servicio(_evidencia(), _usuario())
    tokens.decodificar.return_value = {"tipo": "acceso", "sub": str(uuid4())}

    with pytest.raises(TokenInvalidoException):
        await servicio.canjear("token-acceso")
    accesos.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_should_propagar_token_expirado() -> None:
    servicio, _accesos, tokens = _servicio(_evidencia(), _usuario())
    tokens.decodificar.side_effect = TokenExpiradoException()

    with pytest.raises(TokenExpiradoException):
        await servicio.canjear("vencido")


@pytest.mark.asyncio
async def test_should_auditar_denegado_when_usuario_inactivo() -> None:
    usuario = _usuario(activo=False)
    evidencia = _evidencia()
    servicio, accesos, tokens = _servicio(evidencia, usuario)
    tokens.decodificar.return_value = {
        "tipo": TIPO_TOKEN_DESCARGA,
        "sub": str(usuario.id),
        "evidencia_id": str(evidencia.id),
    }

    with pytest.raises(AccesoDenegadoError):
        await servicio.canjear("jwt")
    acceso = accesos.guardar.await_args.args[0]
    assert acceso.resultado == ResultadoAccesoEvidencia.DENEGADO


@pytest.mark.asyncio
async def test_should_auditar_archivo_ausente_when_raiz_vacia() -> None:
    usuario = _usuario()
    evidencia = _evidencia()
    servicio, accesos, tokens = _servicio(evidencia, usuario, raiz=None)
    tokens.decodificar.return_value = {
        "tipo": TIPO_TOKEN_DESCARGA,
        "sub": str(usuario.id),
        "evidencia_id": str(evidencia.id),
    }

    with pytest.raises(ArchivoNoDisponibleError):
        await servicio.canjear("jwt")
    acceso = accesos.guardar.await_args.args[0]
    assert acceso.resultado == ResultadoAccesoEvidencia.ARCHIVO_NO_DISPONIBLE


@pytest.mark.asyncio
async def test_should_autorizar_when_archivo_esta_dentro_de_la_raiz(tmp_path: Path) -> None:
    usuario = _usuario()
    evidencia = _evidencia()
    destino = tmp_path / "empresas"
    destino.mkdir()
    (destino / "acta.pdf").write_bytes(b"%PDF")
    servicio, accesos, tokens = _servicio(evidencia, usuario, raiz=tmp_path)
    tokens.decodificar.return_value = {
        "tipo": TIPO_TOKEN_DESCARGA,
        "sub": str(usuario.id),
        "evidencia_id": str(evidencia.id),
    }

    archivo = await servicio.canjear("jwt")

    assert archivo.tipo_mime == "application/pdf"
    assert archivo.ruta.is_file()
    acceso = accesos.guardar.await_args.args[0]
    assert acceso.resultado == ResultadoAccesoEvidencia.AUTORIZADO


@pytest.mark.asyncio
async def test_should_no_abrir_ruta_fuera_de_la_raiz(tmp_path: Path) -> None:
    usuario = _usuario()
    evidencia = _evidencia()
    evidencia.ruta_almacenamiento = "../secreto.pdf"
    fuera = tmp_path.parent / "secreto.pdf"
    fuera.write_bytes(b"no")
    servicio, accesos, tokens = _servicio(evidencia, usuario, raiz=tmp_path)
    tokens.decodificar.return_value = {
        "tipo": TIPO_TOKEN_DESCARGA,
        "sub": str(usuario.id),
        "evidencia_id": str(evidencia.id),
    }

    with pytest.raises(ArchivoNoDisponibleError):
        await servicio.canjear("jwt")
    accesos.guardar.assert_awaited()
    fuera.unlink(missing_ok=True)
