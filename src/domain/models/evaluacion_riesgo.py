"""Entidad de dominio `EvaluacionRiesgo` — GTC 45 Anexo A (NP/NR derivados)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.matriz_riesgo import ValorGtcInvalidoError
from src.domain.models.gtc45 import (
    ACEPTABILIDAD_POR_INTERPRETACION,
    NC_VALIDOS,
    ND_VALIDOS,
    NE_VALIDOS,
    AceptabilidadRiesgo,
    InterpretacionNR,
)


def interpretar_nr(nivel_riesgo: int) -> InterpretacionNR:
    """Asigna interpretación NR según tabla A.3 (incluye NR=0 → IV, decisión D1)."""
    if 600 <= nivel_riesgo <= 4000:
        return InterpretacionNR.I
    if 150 <= nivel_riesgo <= 500:
        return InterpretacionNR.II
    if 40 <= nivel_riesgo <= 120:
        return InterpretacionNR.III
    if 0 <= nivel_riesgo <= 20:
        return InterpretacionNR.IV
    raise ValorGtcInvalidoError(
        f"Nivel de riesgo {nivel_riesgo} no encaja en los rangos de la tabla A.3"
    )


@dataclass
class EvaluacionRiesgo:
    """Evaluación de un peligro con índices derivados (nunca aceptados del cliente)."""

    id: UUID | None
    peligro_id: UUID
    nivel_deficiencia: int
    nivel_exposicion: int
    nivel_consecuencia: int
    nivel_probabilidad: int
    nivel_riesgo: int
    interpretacion_nr: InterpretacionNR
    aceptabilidad: AceptabilidadRiesgo
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        peligro_id: UUID,
        nivel_deficiencia: int,
        nivel_exposicion: int,
        nivel_consecuencia: int,
    ) -> "EvaluacionRiesgo":
        """Factoría: valida ND/NE/NC y calcula NP, NR, interpretación y aceptabilidad."""
        nd, ne, nc = cls._validar_nd_ne_nc(nivel_deficiencia, nivel_exposicion, nivel_consecuencia)
        np = nd * ne
        nr = np * nc
        interpretacion = interpretar_nr(nr)
        aceptabilidad = ACEPTABILIDAD_POR_INTERPRETACION[interpretacion]
        return cls(
            id=None,
            peligro_id=peligro_id,
            nivel_deficiencia=nd,
            nivel_exposicion=ne,
            nivel_consecuencia=nc,
            nivel_probabilidad=np,
            nivel_riesgo=nr,
            interpretacion_nr=interpretacion,
            aceptabilidad=aceptabilidad,
        )

    def recalcular(
        self,
        nivel_deficiencia: int,
        nivel_exposicion: int,
        nivel_consecuencia: int,
    ) -> None:
        """Reemplaza ND/NE/NC y recalcula derivados (PUT upsert)."""
        nd, ne, nc = self._validar_nd_ne_nc(nivel_deficiencia, nivel_exposicion, nivel_consecuencia)
        self.nivel_deficiencia = nd
        self.nivel_exposicion = ne
        self.nivel_consecuencia = nc
        self.nivel_probabilidad = nd * ne
        self.nivel_riesgo = self.nivel_probabilidad * nc
        self.interpretacion_nr = interpretar_nr(self.nivel_riesgo)
        self.aceptabilidad = ACEPTABILIDAD_POR_INTERPRETACION[self.interpretacion_nr]
        self.fecha_actualizacion = datetime.now(UTC)

    @staticmethod
    def _validar_nd_ne_nc(nd: int, ne: int, nc: int) -> tuple[int, int, int]:
        if nd not in ND_VALIDOS:
            raise ValorGtcInvalidoError(
                f"Nivel de deficiencia inválido: {nd}; debe ser uno de {sorted(ND_VALIDOS)}"
            )
        if ne not in NE_VALIDOS:
            raise ValorGtcInvalidoError(
                f"Nivel de exposición inválido: {ne}; debe ser uno de {sorted(NE_VALIDOS)}"
            )
        if nc not in NC_VALIDOS:
            raise ValorGtcInvalidoError(
                f"Nivel de consecuencia inválido: {nc}; debe ser uno de {sorted(NC_VALIDOS)}"
            )
        return nd, ne, nc
