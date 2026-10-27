"""Pruebas unitarias para AnalisisService demostrando testabilidad e inyección de dependencias."""
from unittest.mock import MagicMock
import pytest

from sgb.application.analisis_service import AnalisisService
from sgb.domain.datos_abiertos.entities import (
    CruceDivipolaResultado,
    EstadisticasBibliotecas,
    EstadisticasDescriptivas,
)
from sgb.domain.datos_abiertos.ports import AnalisisPort, BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import FuenteExternaError


@pytest.fixture
def service_mocks():
    """Fixture que crea los mocks de los tres puertos y el servicio inyectado."""
    bib = MagicMock(spec=BibliotecasPort)
    div = MagicMock(spec=DivipolaPort)
    ana = MagicMock(spec=AnalisisPort)
    svc = AnalisisService(bibliotecas_port=bib, divipola_port=div, analisis_port=ana)
    return svc, bib, div, ana


def test_analisis_service_demuestra_testabilidad_por_mocks(service_mocks):
    """Demuestra que el servicio puede ser probado de forma determinista y sin red ni BD."""
    svc, mock_bib, mock_div, mock_ana = service_mocks

    mock_bib.obtener_bibliotecas.return_value = ["fake_bib_1", "fake_bib_2"]
    mock_div.obtener_municipios.return_value = ["fake_mpio_1"]

    fake_resultado = CruceDivipolaResultado(
        bibliotecas_por_departamento=[],
        total_municipios_divipola=1,
        municipios_sin_biblioteca=0,
        estadisticas_distribucion=EstadisticasDescriptivas(media=2.0, mediana=2.0, minimo=2, maximo=2),
    )
    mock_ana.cruzar_con_divipola.return_value = fake_resultado

    resultado = svc.obtener_cruce_divipola(limite_bibliotecas=10, limite_divipola=20)

    assert resultado == fake_resultado
    mock_bib.obtener_bibliotecas.assert_called_once_with(limite=10)
    mock_div.obtener_municipios.assert_called_once_with(limite=20)
    mock_ana.cruzar_con_divipola.assert_called_once_with(["fake_bib_1", "fake_bib_2"], ["fake_mpio_1"])


def test_obtener_estadisticas_bibliotecas_orquesta_puertos(service_mocks):
    svc, mock_bib, mock_div, mock_ana = service_mocks

    mock_bib.obtener_bibliotecas.return_value = ["bib1"]
    fake_stats = EstadisticasBibliotecas(
        total_bibliotecas=1, total_municipios_con_biblioteca=1, porcentaje_con_correo=100.0, top_municipios=[]
    )
    mock_ana.analizar_bibliotecas.return_value = fake_stats

    res = svc.obtener_estadisticas_bibliotecas(limite=50)

    assert res == fake_stats
    mock_bib.obtener_bibliotecas.assert_called_once_with(limite=50)
    mock_ana.analizar_bibliotecas.assert_called_once_with(["bib1"])
    mock_div.obtener_municipios.assert_not_called()


@pytest.mark.parametrize("failing_port", ["bib", "div"])
def test_analisis_service_propaga_fuente_externa_error(service_mocks, failing_port):
    svc, mock_bib, mock_div, mock_ana = service_mocks
    err = FuenteExternaError("API externa caida")

    if failing_port == "bib":
        mock_bib.obtener_bibliotecas.side_effect = err
    else:
        mock_bib.obtener_bibliotecas.return_value = []
        mock_div.obtener_municipios.side_effect = err

    with pytest.raises(FuenteExternaError, match="API externa caida"):
        svc.obtener_cruce_divipola()

    mock_ana.cruzar_con_divipola.assert_not_called()
