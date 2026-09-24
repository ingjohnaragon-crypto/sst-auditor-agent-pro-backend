"""Implementación SQLAlchemy del puerto `RepositorioAccesoEvidencia`."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.acceso_evidencia import AccesoEvidencia, ResultadoAccesoEvidencia
from src.domain.repositories.repositorio_acceso_evidencia import RepositorioAccesoEvidencia
from src.infrastructure.database.modelos.acceso_evidencia_orm import AccesoEvidenciaORM


class RepositorioAccesoEvidenciaSQLAlchemy(RepositorioAccesoEvidencia):
    """Persistencia de la auditoría de descargas."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, acceso: AccesoEvidencia) -> AccesoEvidencia:
        fila = AccesoEvidenciaORM(
            id=acceso.id if acceso.id is not None else uuid4(),
            evidencia_id=acceso.evidencia_id,
            usuario_id=acceso.usuario_id,
            resultado=acceso.resultado.value,
            fecha=acceso.fecha,
        )
        self._sesion.add(fila)
        await self._sesion.flush()
        await self._sesion.refresh(fila)
        return AccesoEvidencia(
            id=fila.id,
            evidencia_id=fila.evidencia_id,
            usuario_id=fila.usuario_id,
            resultado=ResultadoAccesoEvidencia(fila.resultado),
            fecha=fila.fecha,
        )
