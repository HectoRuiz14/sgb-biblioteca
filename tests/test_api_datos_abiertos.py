"""Pruebas de los endpoints de datos abiertos y analítica DuckDB."""
from unittest.mock import MagicMock
import pytest

from sgb.api.deps import (
    get_analisis_service,
    get_bibliotecas_adapter,
    get_divipola_adapter,
)
from sgb.domain.datos_abiertos.entities import (
    CruceDivipolaResultado,
    DepartamentoConteo,
    EstadisticasBibliotecas,
    EstadisticasDescriptivas,
    MunicipioConteo,
)
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError
from sgb.infrastructure.resilience import CircuitState
from sgb.main import app

FAKE_STATS = EstadisticasBibliotecas(
    total_bibliotecas=42,
    total_municipios_con_biblioteca=15,
    porcentaje_con_correo=80.0,
    top_municipios=[MunicipioConteo(municipio="BUCARAMANGA", total_bibliotecas=10)],
)

FAKE_CRUCE = CruceDivipolaResultado(
    bibliotecas_por_departamento=[DepartamentoConteo(departamento="SANTANDER", total_bibliotecas=42)],
    total_municipios_divipola=87,
    municipios_sin_biblioteca=72,
    estadisticas_distribucion=EstadisticasDescriptivas(media=0.48, mediana=0.0, minimo=0, maximo=10),
)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.obtener_estadisticas_bibliotecas.return_value = FAKE_STATS
    svc.obtener_cruce_divipola.return_value = FAKE_CRUCE
    app.dependency_overrides[get_analisis_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_analisis_service, None)


def test_get_estadisticas_exitoso_200(client, mock_service):
    r = client.get("/api/v1/datos-abiertos/estadisticas?limite=100")
    assert r.status_code == 200
    data = r.json()
    assert data["total_bibliotecas"] == 42
    assert data["total_municipios_con_biblioteca"] == 15
    assert data["porcentaje_con_correo"] == 80.0
    assert len(data["top_municipios"]) == 1
    assert data["top_municipios"][0]["municipio"] == "BUCARAMANGA"
    mock_service.obtener_estadisticas_bibliotecas.assert_called_once_with(limite=100)


def test_get_cruce_divipola_exitoso_200(client, mock_service):
    r = client.get("/api/v1/datos-abiertos/cruce-divipola?limite_bibliotecas=50&limite_divipola=100")
    assert r.status_code == 200
    data = r.json()
    assert data["total_municipios_divipola"] == 87
    assert data["municipios_sin_biblioteca"] == 72
    assert data["estadisticas_distribucion"]["media"] == 0.48
    assert len(data["bibliotecas_por_departamento"]) == 1
    mock_service.obtener_cruce_divipola.assert_called_once_with(limite_bibliotecas=50, limite_divipola=100)


@pytest.mark.parametrize("endpoint", ["/api/v1/datos-abiertos/estadisticas", "/api/v1/datos-abiertos/cruce-divipola"])
@pytest.mark.parametrize(
    "error_instance,status_code",
    [
        (FuenteExternaError("Fallo conexion SODA"), 503),
        (CircuitoAbiertoError("Circuito OPEN"), 503),
    ],
)
def test_endpoints_retornan_503_ante_fallos_resiliencia(client, endpoint, error_instance, status_code):
    svc = MagicMock()
    svc.obtener_estadisticas_bibliotecas.side_effect = error_instance
    svc.obtener_cruce_divipola.side_effect = error_instance
    app.dependency_overrides[get_analisis_service] = lambda: svc

    try:
        r = client.get(endpoint)
        assert r.status_code == status_code
        assert "detail" in r.json()
    finally:
        app.dependency_overrides.pop(get_analisis_service, None)


def test_get_estado_circuitos_200(client):
    mock_bib = MagicMock()
    mock_bib.breaker.state = CircuitState.CLOSED
    mock_div = MagicMock()
    mock_div.breaker.state = CircuitState.OPEN

    app.dependency_overrides[get_bibliotecas_adapter] = lambda: mock_bib
    app.dependency_overrides[get_divipola_adapter] = lambda: mock_div

    try:
        r = client.get("/api/v1/datos-abiertos/estado-circuitos")
        assert r.status_code == 200
        data = r.json()
        assert data["bibliotecas"] == "CLOSED"
        assert data["divipola"] == "OPEN"
    finally:
        app.dependency_overrides.pop(get_bibliotecas_adapter, None)
        app.dependency_overrides.pop(get_divipola_adapter, None)
