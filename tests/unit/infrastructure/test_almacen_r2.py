"""Pruebas de AlmacenR2, fábrica y doble en memoria (sin red)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from src.domain.exceptions.evidencia import AlmacenamientoNoConfiguradoError
from src.infrastructure.almacenamiento.almacen_local import AlmacenLocal
from src.infrastructure.almacenamiento.almacen_memoria import AlmacenMemoria
from src.infrastructure.almacenamiento.almacen_r2 import AlmacenR2, crear_almacen_r2
from src.infrastructure.config.settings import Settings

SECRETO_VALIDO = "secreto-de-firma-para-pruebas-de-32-caracteres!!"
URL_PRUEBAS = "sqlite+aiosqlite:///:memory:"
CLAVE = "evidencias/00000000-0000-0000-0000-000000000001/prueba.pdf"
PDF = b"%PDF-1.4 contenido-de-prueba"


def _settings(**extras: str | None) -> Settings:
    base: dict[str, str | None] = {
        "jwt_secreto": SECRETO_VALIDO,
        "url_base_datos": URL_PRUEBAS,
        "r2_account_id": "cuenta-dev",
        "r2_access_key_id": "akid",
        "r2_secret_access_key": "secret",
        "r2_bucket": "sst-auditor-dev",
        "r2_endpoint": "https://cuenta-dev.r2.cloudflarestorage.com",
    }
    base.update(extras)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _client_error(codigo: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": codigo, "Message": "no"}},
        operation_name="GetObject",
    )


def test_should_lanzar_when_faltan_variables_r2() -> None:
    settings = _settings(r2_secret_access_key=None)

    with pytest.raises(AlmacenamientoNoConfiguradoError):
        crear_almacen_r2(settings)


def test_should_lanzar_when_variable_r2_vacia() -> None:
    settings = _settings(r2_bucket="   ")

    assert settings.r2_bucket is None
    with pytest.raises(AlmacenamientoNoConfiguradoError):
        crear_almacen_r2(settings)


def test_should_no_crear_cliente_when_r2_incompleto() -> None:
    settings = _settings(r2_endpoint=None)

    with patch("src.infrastructure.almacenamiento.almacen_r2.boto3.client") as mock_client:
        with pytest.raises(AlmacenamientoNoConfiguradoError):
            crear_almacen_r2(settings)
        mock_client.assert_not_called()


def test_should_crear_cliente_s3_when_r2_completo() -> None:
    settings = _settings()
    fake = MagicMock()

    with patch(
        "src.infrastructure.almacenamiento.almacen_r2.boto3.client",
        return_value=fake,
    ) as mock_client:
        almacen = crear_almacen_r2(settings)

    mock_client.assert_called_once_with(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    assert isinstance(almacen, AlmacenR2)


def test_should_llamar_put_object_when_guardar() -> None:
    cliente = MagicMock()
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    almacen.guardar(CLAVE, PDF)

    cliente.put_object.assert_called_once_with(
        Bucket="sst-auditor-dev",
        Key=CLAVE,
        Body=PDF,
    )


def test_should_devolver_bytes_when_leer() -> None:
    cuerpo = MagicMock()
    cuerpo.read.return_value = PDF
    cliente = MagicMock()
    cliente.get_object.return_value = {"Body": cuerpo}
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    assert almacen.leer(CLAVE) == PDF
    cliente.get_object.assert_called_once_with(Bucket="sst-auditor-dev", Key=CLAVE)


def test_should_lanzar_file_not_found_when_clave_inexistente() -> None:
    cliente = MagicMock()
    cliente.get_object.side_effect = _client_error("NoSuchKey")
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    with pytest.raises(FileNotFoundError):
        almacen.leer(CLAVE)


def test_should_propagar_client_error_when_codigo_distinto() -> None:
    cliente = MagicMock()
    cliente.get_object.side_effect = _client_error("AccessDenied")
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    with pytest.raises(ClientError):
        almacen.leer(CLAVE)


def test_should_lanzar_type_error_when_body_sin_read() -> None:
    cliente = MagicMock()
    cliente.get_object.return_value = {"Body": object()}
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    with pytest.raises(TypeError, match="Body.read"):
        almacen.leer(CLAVE)


def test_should_llamar_delete_object_when_eliminar() -> None:
    cliente = MagicMock()
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    almacen.eliminar(CLAVE)

    cliente.delete_object.assert_called_once_with(Bucket="sst-auditor-dev", Key=CLAVE)


def test_should_no_fallar_when_eliminar_objeto_ausente() -> None:
    cliente = MagicMock()
    cliente.delete_object.return_value = {}
    almacen = AlmacenR2(cliente=cliente, bucket="sst-auditor-dev")

    almacen.eliminar("evidencias/x/no-existe.pdf")


def test_should_guardar_leer_y_eliminar_en_memoria() -> None:
    almacen = AlmacenMemoria()

    almacen.guardar(CLAVE, PDF)
    assert almacen.leer(CLAVE) == PDF

    almacen.eliminar(CLAVE)
    with pytest.raises(FileNotFoundError):
        almacen.leer(CLAVE)

    almacen.eliminar(CLAVE)  # idempotente


def test_should_leer_y_rechazar_escape_en_almacen_local(tmp_path: Path) -> None:
    almacen = AlmacenLocal(tmp_path)
    relativa = "evidencias/empresa/archivo.pdf"
    almacen.guardar(relativa, PDF)

    assert almacen.leer(relativa) == PDF

    with pytest.raises(FileNotFoundError):
        almacen.leer("evidencias/empresa/no-existe.pdf")

    with pytest.raises(ValueError):
        almacen.leer("../fuera.pdf")
