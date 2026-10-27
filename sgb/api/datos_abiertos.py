"""Router de FastAPI para consultas analíticas de datos abiertos con DuckDB."""
from fastapi import APIRouter, Depends, HTTPException, Query

from sgb.api.deps import (
    get_analisis_service,
    get_bibliotecas_adapter,
    get_divipola_adapter,
)
from sgb.api.schemas import (
    CruceDivipolaOut,
    ErrorOut,
    EstadisticasBibliotecasOut,
    EstadoCircuitosOut,
)
from sgb.application.analisis_service import AnalisisService
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError
from sgb.infrastructure.datos_abiertos.adapters import (
    BibliotecasDatosGovAdapter,
    DaneDivipolaAdapter,
)

router = APIRouter(prefix="/api/v1/datos-abiertos", tags=["Datos Abiertos y Analítica"])


@router.get(
    "/estadisticas",
    response_model=EstadisticasBibliotecasOut,
    summary="Estadísticas de bibliotecas públicas",
    description="Devuelve métricas agregadas y ranking de municipios con más bibliotecas usando DuckDB.",
    responses={
        503: {"model": ErrorOut, "description": "Fuente externa no disponible o circuito abierto"},
    },
)
def obtener_estadisticas_bibliotecas(
    limite: int = Query(200, ge=1, le=2000, description="Límite de registros a consultar de la API de bibliotecas"),
    service: AnalisisService = Depends(get_analisis_service),
):
    try:
        res = service.obtener_estadisticas_bibliotecas(limite=limite)
        return EstadisticasBibliotecasOut(
            total_bibliotecas=res.total_bibliotecas,
            total_municipios_con_biblioteca=res.total_municipios_con_biblioteca,
            porcentaje_con_correo=res.porcentaje_con_correo,
            top_municipios=[
                {"municipio": m.municipio, "total_bibliotecas": m.total_bibliotecas}
                for m in res.top_municipios
            ],
        )
    except (FuenteExternaError, CircuitoAbiertoError) as e:
        raise HTTPException(503, str(e))


@router.get(
    "/cruce-divipola",
    response_model=CruceDivipolaOut,
    summary="Cruce analítico de bibliotecas con DANE DIVIPOLA",
    description="Ejecuta cruce SQL en DuckDB por municipio normalizado, calculando cobertura por departamento y estadísticas.",
    responses={
        503: {"model": ErrorOut, "description": "Fuente externa no disponible o circuito abierto"},
    },
)
def obtener_cruce_divipola(
    limite_bibliotecas: int = Query(200, ge=1, le=2000),
    limite_divipola: int = Query(1200, ge=1, le=5000),
    service: AnalisisService = Depends(get_analisis_service),
):
    try:
        res = service.obtener_cruce_divipola(
            limite_bibliotecas=limite_bibliotecas,
            limite_divipola=limite_divipola,
        )
        return CruceDivipolaOut(
            bibliotecas_por_departamento=[
                {"departamento": d.departamento, "total_bibliotecas": d.total_bibliotecas}
                for d in res.bibliotecas_por_departamento
            ],
            total_municipios_divipola=res.total_municipios_divipola,
            municipios_sin_biblioteca=res.municipios_sin_biblioteca,
            estadisticas_distribucion={
                "media": res.estadisticas_distribucion.media,
                "mediana": res.estadisticas_distribucion.mediana,
                "minimo": res.estadisticas_distribucion.minimo,
                "maximo": res.estadisticas_distribucion.maximo,
            },
        )
    except (FuenteExternaError, CircuitoAbiertoError) as e:
        raise HTTPException(503, str(e))


@router.get(
    "/estado-circuitos",
    response_model=EstadoCircuitosOut,
    summary="Estado de los Circuit Breakers",
    description="Muestra el estado en tiempo real (CLOSED, OPEN, HALF_OPEN) de los circuitos de las APIs externas.",
)
def obtener_estado_circuitos(
    bib: BibliotecasDatosGovAdapter = Depends(get_bibliotecas_adapter),
    div: DaneDivipolaAdapter = Depends(get_divipola_adapter),
):
    return EstadoCircuitosOut(
        bibliotecas=bib.breaker.state.value,
        divipola=div.breaker.state.value,
    )
