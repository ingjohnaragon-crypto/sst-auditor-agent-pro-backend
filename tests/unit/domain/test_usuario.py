"""Pruebas de la factoría y las invariantes de la entidad `Usuario`."""

import pytest
from src.domain.exceptions.base import DomainException
from src.domain.models.usuario import RolUsuario, Usuario


def test_should_crear_usuario_when_datos_validos() -> None:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="$2b$12$hashdeprueba",
        rol=RolUsuario.AUDITOR_SST,
    )

    assert usuario.id is None
    assert usuario.nombre_completo == "Ana Auditora"
    assert usuario.correo == "ana@empresa.com"
    assert usuario.rol is RolUsuario.AUDITOR_SST
    assert usuario.activo is True
    assert usuario.fecha_creacion is not None
    assert usuario.fecha_actualizacion is not None


def test_should_normalizar_correo_a_minusculas_when_crear() -> None:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="  Ana.Auditora@Empresa.COM ",
        hash_contrasena="$2b$12$hashdeprueba",
        rol=RolUsuario.CONSULTA,
    )

    assert usuario.correo == "ana.auditora@empresa.com"


def test_should_lanzar_error_when_correo_invalido() -> None:
    with pytest.raises(DomainException, match="formato válido"):
        Usuario.crear(
            nombre_completo="Ana Auditora",
            correo="correo-sin-arroba",
            hash_contrasena="$2b$12$hashdeprueba",
            rol=RolUsuario.CONSULTA,
        )


def test_should_lanzar_error_when_nombre_vacio() -> None:
    with pytest.raises(DomainException, match="nombre completo"):
        Usuario.crear(
            nombre_completo="   ",
            correo="ana@empresa.com",
            hash_contrasena="$2b$12$hashdeprueba",
            rol=RolUsuario.CONSULTA,
        )


def test_should_lanzar_error_when_hash_vacio() -> None:
    with pytest.raises(DomainException, match="hash"):
        Usuario.crear(
            nombre_completo="Ana Auditora",
            correo="ana@empresa.com",
            hash_contrasena="",
            rol=RolUsuario.CONSULTA,
        )


def test_should_definir_los_tres_roles_de_sst() -> None:
    assert {rol.value for rol in RolUsuario} == {"ADMINISTRADOR", "AUDITOR_SST", "CONSULTA"}
