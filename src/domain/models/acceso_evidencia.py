"""Registro de un intento de descarga de evidencia."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class ResultadoAccesoEvidencia(StrEnum):
    """Resultado persistido de un canje con token ya válido."""

    AUTORIZADO = "AUTORIZADO"
    ARCHIVO_NO_DISPONIBLE = "ARCHIVO_NO_DISPONIBLE"
    DENEGADO = "DENEGADO"


@dataclass
class AccesoEvidencia:
    """Fila de auditoría. No guarda token, ruta ni bytes."""

    id: UUID | None
    evidencia_id: UUID
    usuario_id: UUID
    resultado: ResultadoAccesoEvidencia
    fecha: datetime

    @classmethod
    def registrar(
        cls,
        evidencia_id: UUID,
        usuario_id: UUID,
        resultado: ResultadoAccesoEvidencia,
    ) -> "AccesoEvidencia":
        """Cierra el resultado y fija la fecha en UTC."""
        return cls(
            id=None,
            evidencia_id=evidencia_id,
            usuario_id=usuario_id,
            resultado=resultado,
            fecha=datetime.now(UTC),
        )
