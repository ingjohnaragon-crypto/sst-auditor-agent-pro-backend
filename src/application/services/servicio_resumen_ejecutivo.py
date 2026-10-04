"""Caso de uso de lectura del resumen ejecutivo por empresa."""

from uuid import UUID

from src.application.dto.respuesta_resumen_ejecutivo import (
    DistribucionRiesgos,
    IrrenunciableResumen,
    RespuestaResumenEjecutivo,
    ResultadoIrrenunciable,
)
from src.domain.exceptions.autoevaluacion import (
    CatalogoIrrenunciableIncompletoError,
    EmpresaNoEncontradaError,
)
from src.domain.models.autoevaluacion import Autoevaluacion
from src.domain.models.gtc45 import InterpretacionNR
from src.domain.repositories.repositorio_autoevaluacion import RepositorioAutoevaluacion
from src.domain.repositories.repositorio_empresa import RepositorioEmpresa
from src.domain.repositories.repositorio_estandar_minimo import RepositorioEstandarMinimo
from src.domain.repositories.repositorio_proceso_actividad import RepositorioProcesoActividad

NUMERALES_IRRENUNCIABLES: tuple[str, ...] = ("1.1.1", "1.1.4")


class ServicioResumenEjecutivo:
    """Arma el resumen con filas persistidas. No llama al motor ni a interpretar_nr."""

    def __init__(
        self,
        repositorio_empresa: RepositorioEmpresa,
        repositorio_autoevaluacion: RepositorioAutoevaluacion,
        repositorio_estandar_minimo: RepositorioEstandarMinimo,
        repositorio_proceso: RepositorioProcesoActividad,
    ) -> None:
        self._empresas = repositorio_empresa
        self._autoevaluaciones = repositorio_autoevaluacion
        self._estandares = repositorio_estandar_minimo
        self._procesos = repositorio_proceso

    async def obtener(self, empresa_id: UUID) -> RespuestaResumenEjecutivo:
        """Devuelve conteos, la última autoevaluación y los irrenunciables."""
        empresa = await self._empresas.buscar_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontradaError()

        autoevaluaciones = await self._autoevaluaciones.listar_por_empresa(empresa_id)
        ultima = self._elegir_ultima(autoevaluaciones)
        conteos = await self._contar_riesgos(empresa_id)
        irrenunciables = await self._armar_irrenunciables(ultima)

        return RespuestaResumenEjecutivo(
            empresa_id=empresa_id,
            cantidad_autoevaluaciones=len(autoevaluaciones),
            autoevaluacion_id=ultima.id if ultima is not None else None,
            requiere_plan_mejora=ultima.requiere_plan_mejora if ultima is not None else False,
            riesgos_nivel_i=conteos[InterpretacionNR.I],
            riesgos_nivel_ii=conteos[InterpretacionNR.II],
            distribucion_riesgos=DistribucionRiesgos.model_validate(
                {
                    "I": conteos[InterpretacionNR.I],
                    "II": conteos[InterpretacionNR.II],
                    "III": conteos[InterpretacionNR.III],
                    "IV": conteos[InterpretacionNR.IV],
                }
            ),
            irrenunciables=irrenunciables,
        )

    @staticmethod
    def _elegir_ultima(autoevaluaciones: list[Autoevaluacion]) -> Autoevaluacion | None:
        if not autoevaluaciones:
            return None
        return max(autoevaluaciones, key=lambda item: (item.fecha, item.fecha_creacion))

    async def _contar_riesgos(self, empresa_id: UUID) -> dict[InterpretacionNR, int]:
        conteos = {nivel: 0 for nivel in InterpretacionNR}
        matriz = await self._procesos.obtener_matriz_por_empresa(empresa_id)
        for nodo in matriz:
            for peligro in nodo["peligros"]:
                evaluacion = peligro["evaluacion"]
                if evaluacion is None:
                    continue
                conteos[evaluacion.interpretacion_nr] += 1
        return conteos

    async def _armar_irrenunciables(
        self,
        ultima: Autoevaluacion | None,
    ) -> list[IrrenunciableResumen]:
        catalogo = await self._estandares.listar()
        por_numeral = {estandar.numeral: estandar for estandar in catalogo}
        items: list[IrrenunciableResumen] = []
        for numeral in NUMERALES_IRRENUNCIABLES:
            estandar = por_numeral.get(numeral)
            if estandar is None:
                raise CatalogoIrrenunciableIncompletoError()
            resultado: ResultadoIrrenunciable = "SIN_CALIFICAR"
            if ultima is not None:
                calificacion = ultima.calificaciones.get(estandar.id)
                if calificacion is not None:
                    resultado = calificacion.resultado.value
            items.append(
                IrrenunciableResumen(
                    numeral=numeral,
                    descripcion=estandar.descripcion,
                    resultado=resultado,
                )
            )
        return items
