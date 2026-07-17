"""Entidad de dominio `Empresa` — sin dependencias de framework."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.domain.exceptions.autoevaluacion import DatosEmpresaInvalidosError

NIVELES_RIESGO_ARL = ("I", "II", "III", "IV", "V")


@dataclass
class Empresa:
    """Empresa evaluada bajo el SG-SST (Res. 0312)."""

    id: UUID | None
    razon_social: str
    nit: str
    actividad_economica: str
    nivel_riesgo_arl: str
    numero_trabajadores: int
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        razon_social: str,
        nit: str,
        actividad_economica: str,
        nivel_riesgo_arl: str,
        numero_trabajadores: int,
    ) -> "Empresa":
        """Factoría que valida invariantes de negocio."""
        razon = razon_social.strip()
        if not razon:
            raise DatosEmpresaInvalidosError("La razón social no puede estar vacía")
        nit_limpio = nit.strip()
        if not nit_limpio:
            raise DatosEmpresaInvalidosError("El NIT no puede estar vacío")
        actividad = actividad_economica.strip()
        if not actividad:
            raise DatosEmpresaInvalidosError("La actividad económica no puede estar vacía")
        nivel = nivel_riesgo_arl.strip().upper()
        if nivel not in NIVELES_RIESGO_ARL:
            raise DatosEmpresaInvalidosError(
                f"El nivel de riesgo ARL debe ser uno de {', '.join(NIVELES_RIESGO_ARL)}"
            )
        if numero_trabajadores <= 0:
            raise DatosEmpresaInvalidosError("El número de trabajadores debe ser mayor que 0")
        return cls(
            id=None,
            razon_social=razon,
            nit=nit_limpio,
            actividad_economica=actividad,
            nivel_riesgo_arl=nivel,
            numero_trabajadores=numero_trabajadores,
        )
