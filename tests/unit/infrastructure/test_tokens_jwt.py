"""Pruebas de la implementación PyJWT del puerto de tokens."""

from uuid import uuid4

import jwt
import pytest
from src.domain.exceptions.autenticacion import TokenExpiradoException, TokenInvalidoException
from src.domain.models.usuario import RolUsuario, Usuario
from src.infrastructure.config.settings import Settings
from src.infrastructure.security.tokens_jwt import TokensJWT

SECRETO_PRUEBAS = "secreto-de-firma-para-pruebas-de-32-caracteres!!"
OTRO_SECRETO = "otro-secreto-distinto-tambien-de-32-caracteres!!"


def construir_settings(**ajustes: object) -> Settings:
    valores: dict[str, object] = {
        "url_base_datos": "sqlite+aiosqlite:///:memory:",
        "jwt_secreto": SECRETO_PRUEBAS,
    }
    valores.update(ajustes)
    return Settings(_env_file=None, **valores)  # type: ignore[arg-type]


def construir_usuario() -> Usuario:
    usuario = Usuario.crear(
        nombre_completo="Ana Auditora",
        correo="ana@empresa.com",
        hash_contrasena="$2b$12$hash",
        rol=RolUsuario.AUDITOR_SST,
    )
    usuario.id = uuid4()
    return usuario


def test_should_incluir_claims_requeridos_en_token_de_acceso() -> None:
    usuario = construir_usuario()
    servicio = TokensJWT(construir_settings())

    claims = servicio.decodificar(servicio.emitir_token_acceso(usuario))

    assert claims["sub"] == str(usuario.id)
    assert claims["rol"] == "AUDITOR_SST"
    assert claims["tipo"] == "acceso"
    assert "iat" in claims
    assert "exp" in claims
    assert "jti" in claims


def test_should_emitir_token_de_refresco_sin_claim_rol() -> None:
    usuario = construir_usuario()
    servicio = TokensJWT(construir_settings())

    claims = servicio.decodificar(servicio.emitir_token_refresco(usuario))

    assert claims["tipo"] == "refresco"
    assert claims["sub"] == str(usuario.id)
    assert "rol" not in claims


def test_should_emitir_jti_unico_por_token() -> None:
    usuario = construir_usuario()
    servicio = TokensJWT(construir_settings())

    primero = servicio.decodificar(servicio.emitir_token_acceso(usuario))
    segundo = servicio.decodificar(servicio.emitir_token_acceso(usuario))

    assert primero["jti"] != segundo["jti"]


def test_should_lanzar_token_invalido_when_firma_invalida() -> None:
    usuario = construir_usuario()
    token_ajeno = TokensJWT(construir_settings(jwt_secreto=OTRO_SECRETO)).emitir_token_acceso(
        usuario
    )
    servicio = TokensJWT(construir_settings())

    with pytest.raises(TokenInvalidoException):
        servicio.decodificar(token_ajeno)


def test_should_lanzar_token_invalido_when_algoritmo_none() -> None:
    usuario = construir_usuario()
    token_sin_firma = jwt.encode({"sub": str(usuario.id), "tipo": "acceso"}, None, algorithm="none")
    servicio = TokensJWT(construir_settings())

    with pytest.raises(TokenInvalidoException):
        servicio.decodificar(token_sin_firma)


def test_should_lanzar_token_expirado_when_token_vencido() -> None:
    usuario = construir_usuario()
    servicio_vencido = TokensJWT(construir_settings(jwt_minutos_expiracion_acceso=-1))
    token_vencido = servicio_vencido.emitir_token_acceso(usuario)

    with pytest.raises(TokenExpiradoException):
        TokensJWT(construir_settings()).decodificar(token_vencido)


def test_should_lanzar_token_invalido_when_token_corrupto() -> None:
    servicio = TokensJWT(construir_settings())

    with pytest.raises(TokenInvalidoException):
        servicio.decodificar("no.es.un-jwt")
