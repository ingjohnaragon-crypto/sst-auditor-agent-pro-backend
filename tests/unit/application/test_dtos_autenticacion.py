"""Pruebas de los DTOs de autenticación y del mapper de usuario."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.application.dto.respuesta_tokens import RespuestaTokenAcceso, RespuestaTokens
from src.application.dto.solicitud_login import SolicitudLogin
from src.application.mappers.mapper_usuario import MapperUsuario
from src.domain.exceptions.autenticacion import TokenInvalidoException
from src.domain.models.usuario import RolUsuario, Usuario


def test_should_normalizar_correo_a_minusculas_when_login() -> None:
    dto = SolicitudLogin(correo="Ana.Auditora@Empresa.COM", contrasena="Contrasena123")

    assert dto.correo == "ana.auditora@empresa.com"


def test_should_ocultar_contrasena_en_repr_y_serializacion() -> None:
    dto = SolicitudLogin(correo="ana@empresa.com", contrasena="Contrasena123")

    assert "Contrasena123" not in repr(dto)
    assert "Contrasena123" not in str(dto.model_dump())


def test_should_rechazar_contrasena_menor_a_8_caracteres() -> None:
    with pytest.raises(ValidationError):
        SolicitudLogin(correo="ana@empresa.com", contrasena="corta")


def test_should_rechazar_correo_con_formato_invalido() -> None:
    with pytest.raises(ValidationError):
        SolicitudLogin(correo="no-es-un-correo", contrasena="Contrasena123")


def test_should_usar_tipo_bearer_por_defecto_en_respuestas_de_tokens() -> None:
    tokens = RespuestaTokens(token_acceso="a", token_refresco="r", expira_en_segundos=1800)
    acceso = RespuestaTokenAcceso(token_acceso="a", expira_en_segundos=1800)

    assert tokens.tipo_token == "Bearer"
    assert acceso.tipo_token == "Bearer"


def test_should_mapear_usuario_a_respuesta_sin_hash() -> None:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="$2b$12$hash",
        rol=RolUsuario.ADMINISTRADOR,
    )
    usuario.id = uuid4()

    respuesta = MapperUsuario.a_respuesta(usuario)

    assert respuesta.id == usuario.id
    assert respuesta.nombre_completo == "Ana Auditora"
    assert respuesta.correo == "ana@empresa.com"
    assert respuesta.rol == "ADMINISTRADOR"
    assert "hash" not in respuesta.model_dump_json()


def test_should_lanzar_token_invalido_when_mapear_usuario_sin_id() -> None:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="$2b$12$hash",
        rol=RolUsuario.CONSULTA,
    )

    with pytest.raises(TokenInvalidoException):
        MapperUsuario.a_respuesta(usuario)
