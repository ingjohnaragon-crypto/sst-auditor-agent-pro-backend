"""DTOs de solicitud y respuesta para la matriz GTC 45."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ClasificacionLiteral = Literal[
    "BIOLOGICO",
    "FISICO",
    "QUIMICO",
    "PSICOSOCIAL",
    "BIOMECANICO",
    "CONDICIONES_SEGURIDAD",
    "FENOMENOS_NATURALES",
]
TipoControlLiteral = Literal[
    "ELIMINACION",
    "SUSTITUCION",
    "INGENIERIA",
    "ADMINISTRATIVO",
    "EPP",
]
InterpretacionLiteral = Literal["I", "II", "III", "IV"]
AceptabilidadLiteral = Literal[
    "NO_ACEPTABLE",
    "ACEPTABLE_CON_CONTROL",
    "MEJORABLE",
    "ACEPTABLE",
]


class SolicitudCrearProcesoActividad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=150)
    es_rutinaria: bool
    zona_lugar: str | None = Field(default=None, max_length=150)


class SolicitudActualizarProcesoActividad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    es_rutinaria: bool | None = None
    zona_lugar: str | None = Field(default=None, max_length=150)


class RespuestaProcesoActividad(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    es_rutinaria: bool
    zona_lugar: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SolicitudCrearPeligro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clasificacion: ClasificacionLiteral
    descripcion: str = Field(min_length=1)
    efectos_posibles: str | None = None


class SolicitudActualizarPeligro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clasificacion: ClasificacionLiteral | None = None
    descripcion: str | None = Field(default=None, min_length=1)
    efectos_posibles: str | None = None


class RespuestaPeligro(BaseModel):
    id: UUID
    proceso_actividad_id: UUID
    clasificacion: ClasificacionLiteral
    descripcion: str
    efectos_posibles: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SolicitudUpsertEvaluacion(BaseModel):
    """Solo ND/NE/NC — los derivados se calculan en dominio."""

    model_config = ConfigDict(extra="forbid")

    nivel_deficiencia: int
    nivel_exposicion: int
    nivel_consecuencia: int


class RespuestaEvaluacionRiesgo(BaseModel):
    id: UUID
    peligro_id: UUID
    nivel_deficiencia: int
    nivel_exposicion: int
    nivel_consecuencia: int
    nivel_probabilidad: int
    nivel_riesgo: int
    interpretacion_nr: InterpretacionLiteral
    aceptabilidad: AceptabilidadLiteral
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SolicitudCrearControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoControlLiteral
    descripcion: str = Field(min_length=1)


class SolicitudActualizarControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoControlLiteral | None = None
    descripcion: str | None = Field(default=None, min_length=1)


class RespuestaControlRiesgo(BaseModel):
    id: UUID
    evaluacion_riesgo_id: UUID
    tipo: TipoControlLiteral
    descripcion: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class RespuestaPeligroMatriz(BaseModel):
    peligro: RespuestaPeligro
    evaluacion: RespuestaEvaluacionRiesgo | None
    controles: list[RespuestaControlRiesgo]


class RespuestaProcesoMatriz(BaseModel):
    proceso: RespuestaProcesoActividad
    peligros: list[RespuestaPeligroMatriz]


class RespuestaMatrizRiesgos(BaseModel):
    empresa_id: UUID
    procesos: list[RespuestaProcesoMatriz]
