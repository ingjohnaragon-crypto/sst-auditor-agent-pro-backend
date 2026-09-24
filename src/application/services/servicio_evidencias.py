"""Casos de uso de metadatos de evidencias de soporte."""

from uuid import UUID

from src.application.dto.respuesta_evidencia import RespuestaEvidencia
from src.application.dto.solicitud_registrar_evidencia import SolicitudRegistrarEvidencia
from src.application.mappers.mapper_evidencia import MapperEvidencia
from src.domain.exceptions.evidencia import (
    CalificacionNoEncontradaError,
    EvidenciaNoEncontradaError,
)
from src.domain.models.evidencia import Evidencia
from src.domain.repositories.repositorio_evidencia import RepositorioEvidencia


class ServicioEvidencias:
    """Registra, lista y da de baja metadatos. No recibe el binario."""

    def __init__(self, repositorio: RepositorioEvidencia) -> None:
        self._repositorio = repositorio

    async def registrar(
        self,
        calificacion_id: UUID,
        dto: SolicitudRegistrarEvidencia,
        usuario_id: UUID,
    ) -> RespuestaEvidencia:
        """Persiste metadatos ligados a la calificación. `usuario_id` viene del token."""
        await self._exigir_calificacion(calificacion_id)
        evidencia = Evidencia.crear(
            calificacion_estandar_id=calificacion_id,
            usuario_id=usuario_id,
            nombre_archivo=dto.nombre_archivo,
            tipo_mime=dto.tipo_mime,
            tamano_bytes=dto.tamano_bytes,
            ruta_almacenamiento=dto.ruta_almacenamiento,
        )
        guardada = await self._repositorio.guardar(evidencia)
        return MapperEvidencia.a_respuesta(guardada)

    async def listar_activas(self, calificacion_id: UUID) -> list[RespuestaEvidencia]:
        """Devuelve solo evidencias activas de la calificación."""
        await self._exigir_calificacion(calificacion_id)
        evidencias = await self._repositorio.listar_activas_por_calificacion(calificacion_id)
        return [MapperEvidencia.a_respuesta(item) for item in evidencias]

    async def dar_de_baja(self, evidencia_id: UUID) -> None:
        """Borrado lógico. 404 si no existe; 409 si ya estaba inactiva."""
        evidencia = await self._repositorio.buscar_por_id(evidencia_id)
        if evidencia is None:
            raise EvidenciaNoEncontradaError()
        evidencia.dar_de_baja()
        await self._repositorio.guardar(evidencia)

    async def _exigir_calificacion(self, calificacion_id: UUID) -> None:
        if not await self._repositorio.existe_calificacion(calificacion_id):
            raise CalificacionNoEncontradaError()
