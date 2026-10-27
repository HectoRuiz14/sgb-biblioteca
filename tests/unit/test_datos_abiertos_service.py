"""Pruebas unitarias para DatosAbiertosService demostrando inyección de dependencias con mocks."""
from unittest.mock import MagicMock
import pytest

from sgb.application.datos_abiertos_service import DatosAbiertosService
from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError

SAMPLE_BIBLIOTECAS = [
    BibliotecaPublica(nombre="Biblio Central", municipio="Bucaramanga", correo="c@b.gov.co", telefono="123")
]
SAMPLE_MUNICIPIOS = [
    MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68001",
                      municipio="BUCARAMANGA", tipo="Municipio", longitud="-73.1", latitud="7.1")
]


@pytest.fixture
def service():
    """Fixture que inyecta MagicMocks de los dos puertos en el servicio."""
    bib = MagicMock(spec=BibliotecasPort)
    div = MagicMock(spec=DivipolaPort)
    svc = DatosAbiertosService(bibliotecas_port=bib, divipola_port=div)
    return svc, bib, div


@pytest.mark.parametrize(
    "method_name,port_attr,expected_data,other_port_attr,call_limit",
    [
        ("obtener_bibliotecas", "obtener_bibliotecas", SAMPLE_BIBLIOTECAS, "obtener_municipios", 10),
        ("obtener_municipios", "obtener_municipios", SAMPLE_MUNICIPIOS, "obtener_bibliotecas", 25),
    ],
)
def test_datos_abiertos_service_delegacion_exitosa(
    service, method_name, port_attr, expected_data, other_port_attr, call_limit
):
    svc, mock_bib, mock_div = service
    is_bib = method_name == "obtener_bibliotecas"
    active_mock = mock_bib if is_bib else mock_div
    inactive_mock = mock_div if is_bib else mock_bib

    getattr(active_mock, port_attr).return_value = expected_data
    resultado = getattr(svc, method_name)(limite=call_limit)

    assert resultado == expected_data
    getattr(active_mock, port_attr).assert_called_once_with(limite=call_limit)
    getattr(inactive_mock, other_port_attr).assert_not_called()


@pytest.mark.parametrize(
    "method_name,port_target,exc_cls,exc_msg",
    [
        ("obtener_bibliotecas", "bib", CircuitoAbiertoError, "Circuito ABIERTO"),
        ("obtener_municipios", "div", FuenteExternaError, "Fallo en servicio DANE"),
    ],
)
def test_datos_abiertos_service_propaga_excepciones(service, method_name, port_target, exc_cls, exc_msg):
    svc, mock_bib, mock_div = service
    target = mock_bib if port_target == "bib" else mock_div
    attr = "obtener_bibliotecas" if port_target == "bib" else "obtener_municipios"
    getattr(target, attr).side_effect = exc_cls(exc_msg)

    with pytest.raises(exc_cls, match=exc_msg):
        getattr(svc, method_name)(limite=5)
