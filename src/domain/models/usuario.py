"""Entidad de dominio `Usuario` y enum de roles de SST — sin dependencias de framework."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from src.domain.exceptions.base import DomainException

# Validación de formato de correo propia del dominio (intencionalmente simple:
# la validación estricta RFC la hace Pydantic en la capa de aplicación).
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RolUsuario(StrEnum):
    """Roles de acceso del dominio SST.

    - ADMINISTRADOR: gestión de usuarios y configuración del sistema.
    - AUDITOR_SST: acceso completo a auditorías, información médica ocupacional
      e índices de siniestralidad.
    - CONSULTA: solo lectura de información no sensible.
    """

    ADMINISTRADOR = "ADMINISTRADOR"
    AUDITOR_SST = "AUDITOR_SST"
    CONSULTA = "CONSULTA"


@dataclass
class Usuario:
    """Usuario del sistema con credenciales cifradas (nunca contraseña en claro)."""

    id: UUID | None
    nombre_completo: str
    correo: str
    hash_contrasena: str
    rol: RolUsuario
    activo: bool = True
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def crear(
        cls,
        nombre_completo: str,
        correo: str,
        hash_contrasena: str,
        rol: RolUsuario,
    ) -> "Usuario":
        """Factoría que valida invariantes y normaliza el correo a minúsculas."""
        nombre_limpio = nombre_completo.strip()
        if not nombre_limpio:
            raise DomainException("El nombre completo no puede estar vacío")
        correo_normalizado = correo.strip().lower()
        if not PATRON_CORREO.match(correo_normalizado):
            raise DomainException(f"El correo '{correo_normalizado}' no tiene un formato válido")
        if not hash_contrasena:
            raise DomainException("El hash de la contraseña es obligatorio")
        return cls(
            id=None,
            nombre_completo=nombre_limpio,
            correo=correo_normalizado,
            hash_contrasena=hash_contrasena,
            rol=rol,
        )
