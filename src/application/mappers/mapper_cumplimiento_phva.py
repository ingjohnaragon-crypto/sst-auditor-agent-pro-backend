"""Mapper dominio → DTO de cumplimiento PHVA."""

from uuid import UUID

from src.application.dto.respuesta_cumplimiento_phva import (
    RespuestaCumplimientoFasePHVA,
    RespuestaCumplimientoPHVA,
)
from src.domain.services.motor_calificacion_res312 import ResumenCumplimientoPHVA


class MapperCumplimientoPHVA:
    """Transforma el resumen de dominio en respuesta API."""

    @staticmethod
    def a_respuesta(
        resumen: ResumenCumplimientoPHVA,
        *,
        autoevaluacion_id: UUID,
        empresa_id: UUID,
    ) -> RespuestaCumplimientoPHVA:
        return RespuestaCumplimientoPHVA(
            autoevaluacion_id=autoevaluacion_id,
            empresa_id=empresa_id,
            perfil=resumen.perfil,
            puntaje_total=resumen.puntaje_total,
            umbral_plan_mejora=resumen.umbral_plan_mejora,
            requiere_plan_mejora=resumen.requiere_plan_mejora,
            finalizada=resumen.finalizada,
            fases=[
                RespuestaCumplimientoFasePHVA(
                    ciclo_phva=fase.ciclo_phva,
                    peso_maximo=fase.peso_maximo,
                    puntaje_obtenido=fase.puntaje_obtenido,
                    porcentaje_cumplimiento=fase.porcentaje_cumplimiento,
                    brecha=fase.brecha,
                )
                for fase in resumen.fases
            ],
        )
