"""Emite y canjea enlaces de descarga de evidencias."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from src.application.dto.respuesta_enlace_descarga import RespuestaEnlaceDescarga
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.exceptions.autoevaluacion import AccesoDenegadoError
from src.domain.exceptions.evidencia import ArchivoNoDisponibleError, EvidenciaNoEncontradaError
from src.domain.models.acceso_evidencia import AccesoEvidencia, ResultadoAccesoEvidencia
from src.domain.models.evidencia import Evidencia
from src.domain.models.usuario import RolUsuario, Usuario
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia
from src.domain.repositories.repositorio_usuario import RepositorioUsuario
from src.domain.repositories.servicio_tokens import TIPO_TOKEN_DESCARGA, ServicioTokens


@dataclass(frozen=True)
class ArchivoAutorizado:
    """Ruta ya contenida en la raíz, lista para que el router la sirva."""

    ruta: Path
    tipo_mime: str
    nombre_archivo: str


class ServicioDescargaEvidencia:
    """Autoriza la descarga. No escribe el binario ni abre rutas fuera de la raíz."""

    def __init__(
        self,
        repositorio_evidencia: RepositorioEvidencia,
        repositorio_usuario: RepositorioUsuario,
        repositorio_acceso: RepositorioAccesoEvidencia,
        servicio_tokens: ServicioTokens,
        *,
        segundos_expiracion: int,
        prefijo_api: str,
        raiz_almacenamiento: Path | None,
    ) -> None:
        self._evidencias = repositorio_evidencia
        self._usuarios = repositorio_usuario
        self._accesos = repositorio_acceso
        self._tokens = servicio_tokens
        self._segundos = segundos_expiracion
        self._prefijo = prefijo_api.rstrip("/")
        self._raiz = raiz_almacenamiento

    async def emitir_enlace(self, evidencia_id: UUID, usuario: Usuario) -> RespuestaEnlaceDescarga:
        """Firma un JWT `tipo=descarga` si el rol puede escribir y la evidencia está activa."""
        self._exigir_escritor(usuario)
        evidencia = await self._evidencia_activa(evidencia_id)
        if usuario.id is None or evidencia.id is None:
            raise TokenInvalidoException()
        token = self._tokens.emitir_token_descarga(usuario.id, evidencia.id, self._segundos)
        return RespuestaEnlaceDescarga(
            url=f"{self._prefijo}/descargas/evidencias?token={token}",
            expira_en_segundos=self._segundos,
        )

    async def canjear(self, token: str) -> ArchivoAutorizado:
        """Revalida rol y evidencia, audita y solo entonces resuelve el archivo."""
        claims = self._tokens.decodificar(token)
        if claims.get("tipo") != TIPO_TOKEN_DESCARGA:
            raise TokenInvalidoException()
        usuario_id = _uuid_claim(claims.get("sub"))
        evidencia_id = _uuid_claim(claims.get("evidencia_id"))
        usuario = await self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or not _es_escritor(usuario):
            if usuario is not None:
                await self._auditar(evidencia_id, usuario_id, ResultadoAccesoEvidencia.DENEGADO)
            raise AccesoDenegadoError()
        evidencia = await self._evidencias.buscar_por_id(evidencia_id)
        if evidencia is None or not evidencia.activo:
            raise EvidenciaNoEncontradaError()
        archivo = _resolver_archivo(self._raiz, evidencia)
        if archivo is None:
            await self._auditar(
                evidencia_id, usuario_id, ResultadoAccesoEvidencia.ARCHIVO_NO_DISPONIBLE
            )
            raise ArchivoNoDisponibleError()
        await self._auditar(evidencia_id, usuario_id, ResultadoAccesoEvidencia.AUTORIZADO)
        return archivo

    def _exigir_escritor(self, usuario: Usuario) -> None:
        if not _es_escritor(usuario):
            raise AccesoDenegadoError()

    async def _evidencia_activa(self, evidencia_id: UUID) -> Evidencia:
        evidencia = await self._evidencias.buscar_por_id(evidencia_id)
        if evidencia is None or not evidencia.activo:
            raise EvidenciaNoEncontradaError()
        return evidencia

    async def _auditar(
        self,
        evidencia_id: UUID,
        usuario_id: UUID,
        resultado: ResultadoAccesoEvidencia,
    ) -> None:
        await self._accesos.guardar(AccesoEvidencia.registrar(evidencia_id, usuario_id, resultado))


def _es_escritor(usuario: Usuario) -> bool:
    return usuario.activo and usuario.rol != RolUsuario.CONSULTA


def _uuid_claim(valor: object) -> UUID:
    if not isinstance(valor, str):
        raise TokenInvalidoException()
    try:
        return UUID(valor)
    except ValueError as error:
        raise TokenInvalidoException() from error


def _resolver_archivo(raiz: Path | None, evidencia: Evidencia) -> ArchivoAutorizado | None:
    if raiz is None:
        return None
    raiz_resuelta = raiz.resolve()
    candidata = (raiz_resuelta / evidencia.ruta_almacenamiento).resolve()
    try:
        candidata.relative_to(raiz_resuelta)
    except ValueError:
        return None
    if not candidata.is_file():
        return None
    return ArchivoAutorizado(
        ruta=candidata,
        tipo_mime=evidencia.tipo_mime,
        nombre_archivo=Path(evidencia.nombre_archivo).name,
    )
