"""Pruebas unitarias para DatosAbiertosService demostrando inyección de dependencias con mocks."""
from unittest.mock import MagicMock
import pytest

from sgb.application.datos_abiertos_service import DatosAbiertosService
from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError


@pytest.fixture
def service():
    """Fixture que inyecta MagicMocks de los dos puertos en el servicio."""
    bib = MagicMock(spec=BibliotecasPort)
    div = MagicMock(spec=DivipolaPort)
    svc = DatosAbiertosService(bibliotecas_port=bib, divipola_port=div)
    return svc, bib, div


def test_datos_abiertos_service_obtener_bibliotecas(service):
    svc, mock_bib, mock_div = service

    esperadas = [
        BibliotecaPublica(
            nombre="Biblioteca Central",
            municipio="Bucaramanga",
            correo="contacto@biblio.gov.co",
            telefono="3001234567",
        )
    ]
    mock_bib.obtener_bibliotecas.return_value = esperadas

    resultado = svc.obtener_bibliotecas(limite=10)

    assert resultado == esperadas
    mock_bib.obtener_bibliotecas.assert_called_once_with(limite=10)
    mock_div.obtener_municipios.assert_not_called()


def test_datos_abiertos_service_obtener_municipios(service):
    svc, mock_bib, mock_div = service

    esperados = [
        MunicipioDivipola(
            codigo_departamento="68",
            departamento="SANTANDER",
            codigo_municipio="68001",
            municipio="BUCARAMANGA",
            tipo="Municipio",
            longitud="-73.1198",
            latitud="7.1253",
        )
    ]
    mock_div.obtener_municipios.return_value = esperados

    resultado = svc.obtener_municipios(limite=25)

    assert resultado == esperados
    mock_div.obtener_municipios.assert_called_once_with(limite=25)
    mock_bib.obtener_bibliotecas.assert_not_called()


def test_datos_abiertos_service_propaga_circuito_abierto_error(service):
    svc, mock_bib, _ = service
    mock_bib.obtener_bibliotecas.side_effect = CircuitoAbiertoError("Circuito ABIERTO")

    with pytest.raises(CircuitoAbiertoError, match="Circuito ABIERTO"):
        svc.obtener_bibliotecas(limite=5)


def test_datos_abiertos_service_propaga_fuente_externa_error(service):
    svc, _, mock_div = service
    mock_div.obtener_municipios.side_effect = FuenteExternaError("Fallo en servicio DANE")

    with pytest.raises(FuenteExternaError, match="Fallo en servicio DANE"):
        svc.obtener_municipios(limite=5)
