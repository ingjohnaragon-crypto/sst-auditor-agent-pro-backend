"""Pruebas unitarias de `ServicioEvidencias` con repositorio mockeado."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.application.dto.solicitud_registrar_evidencia import SolicitudRegistrarEvidencia
from src.application.services.servicio_evidencias import ServicioEvidencias
from src.domain.exceptions.evidencia import (
    CalificacionNoEncontradaError,
    EvidenciaNoEncontradaError,
    EvidenciaYaInactivaError,
)
from src.domain.models.evidencia import Evidencia


def _dto() -> SolicitudRegistrarEvidencia:
    return SolicitudRegistrarEvidencia(
        nombre_archivo="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=2048,
        ruta_almacenamiento="empresas/acta.pdf",
    )


def _evidencia(*, activo: bool = True) -> Evidencia:
    evidencia = Evidencia.crear(
        calificacion_estandar_id=uuid4(),
        usuario_id=uuid4(),
        nombre_archivo="acta.pdf",
        tipo_mime="application/pdf",
        tamano_bytes=2048,
        ruta_almacenamiento="empresas/acta.pdf",
    )
    evidencia.id = uuid4()
    evidencia.activo = activo
    if not activo:
        evidencia.fecha_eliminacion = datetime.now(UTC)
    return evidencia


@pytest.mark.asyncio
async def test_should_responder_404_when_calificacion_no_existe() -> None:
    repositorio = AsyncMock()
    repositorio.existe_calificacion.return_value = False
    servicio = ServicioEvidencias(repositorio)

    with pytest.raises(CalificacionNoEncontradaError):
        await servicio.registrar(uuid4(), _dto(), uuid4())
    repositorio.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_should_persistir_usuario_del_argumento_when_registrar() -> None:
    usuario_id = uuid4()
    calificacion_id = uuid4()
    repositorio = AsyncMock()
    repositorio.existe_calificacion.return_value = True

    async def _guardar(evidencia: Evidencia) -> Evidencia:
        evidencia.id = uuid4()
        return evidencia

    repositorio.guardar.side_effect = _guardar
    servicio = ServicioEvidencias(repositorio)

    respuesta = await servicio.registrar(calificacion_id, _dto(), usuario_id)

    assert respuesta.usuario_id == usuario_id
    assert respuesta.calificacion_estandar_id == calificacion_id
    guardada = repositorio.guardar.await_args.args[0]
    assert guardada.usuario_id == usuario_id


@pytest.mark.asyncio
async def test_should_listar_solo_lo_que_devuelve_el_puerto() -> None:
    activa = _evidencia()
    repositorio = AsyncMock()
    repositorio.existe_calificacion.return_value = True
    repositorio.listar_activas_por_calificacion.return_value = [activa]
    servicio = ServicioEvidencias(repositorio)

    listado = await servicio.listar_activas(activa.calificacion_estandar_id)

    assert len(listado) == 1
    assert listado[0].activo is True
    assert listado[0].id == activa.id


@pytest.mark.asyncio
async def test_should_dar_de_baja_when_evidencia_activa() -> None:
    evidencia = _evidencia()
    repositorio = AsyncMock()
    repositorio.buscar_por_id.return_value = evidencia
    servicio = ServicioEvidencias(repositorio)

    await servicio.dar_de_baja(evidencia.id)  # type: ignore[arg-type]

    assert evidencia.activo is False
    repositorio.guardar.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_responder_404_when_evidencia_no_existe() -> None:
    repositorio = AsyncMock()
    repositorio.buscar_por_id.return_value = None
    servicio = ServicioEvidencias(repositorio)

    with pytest.raises(EvidenciaNoEncontradaError):
        await servicio.dar_de_baja(uuid4())


@pytest.mark.asyncio
async def test_should_responder_409_when_ya_esta_inactiva() -> None:
    evidencia = _evidencia(activo=False)
    repositorio = AsyncMock()
    repositorio.buscar_por_id.return_value = evidencia
    servicio = ServicioEvidencias(repositorio)

    with pytest.raises(EvidenciaYaInactivaError):
        await servicio.dar_de_baja(evidencia.id)  # type: ignore[arg-type]
