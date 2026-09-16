"""Entidad de dominio `ControlRiesgo` — GTC 45 / D. 1072 jerarquía de controles."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.matriz_riesgo import DatosControlInvalidosError
from src.domain.models.gtc45 import TipoControl


@dataclass
class ControlRiesgo:
    """Control aplicado sobre una evaluación de riesgo."""

    id: UUID | None
    evaluacion_riesgo_id: UUID
    tipo: TipoControl
    descripcion: str
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        evaluacion_riesgo_id: UUID,
        tipo: str | TipoControl,
        descripcion: str,
    ) -> "ControlRiesgo":
        """Factoría que valida tipo y descripción."""
        try:
            tipo_ctrl = TipoControl(str(tipo).strip().upper())
        except ValueError as exc:
            raise DatosControlInvalidosError(f"Tipo de control inválido: {tipo}") from exc
        desc = descripcion.strip()
        if not desc:
            raise DatosControlInvalidosError("La descripción del control no puede estar vacía")
        return cls(
            id=None,
            evaluacion_riesgo_id=evaluacion_riesgo_id,
            tipo=tipo_ctrl,
            descripcion=desc,
        )

    def actualizar(
        self,
        *,
        tipo: str | TipoControl | None = None,
        descripcion: str | None = None,
    ) -> None:
        """Actualiza campos mutables."""
        if tipo is not None:
            try:
                self.tipo = TipoControl(str(tipo).strip().upper())
            except ValueError as exc:
                raise DatosControlInvalidosError(f"Tipo de control inválido: {tipo}") from exc
        if descripcion is not None:
            desc = descripcion.strip()
            if not desc:
                raise DatosControlInvalidosError("La descripción del control no puede estar vacía")
            self.descripcion = desc
        self.fecha_actualizacion = datetime.now(UTC)
