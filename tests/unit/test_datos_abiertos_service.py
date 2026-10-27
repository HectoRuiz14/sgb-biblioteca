"""Pruebas unitarias para DatosAbiertosService demostrando inyección de dependencias con mocks."""
from unittest.mock import MagicMock
import pytest

from sgb.application.datos_abiertos_service import DatosAbiertosService
from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError


def test_datos_abiertos_service_obtener_bibliotecas():
    mock_bibliotecas_port = MagicMock(spec=BibliotecasPort)
    mock_divipola_port = MagicMock(spec=DivipolaPort)

    bibliotecas_esperadas = [
        BibliotecaPublica(
            nombre="Biblioteca Central",
            municipio="Bucaramanga",
            correo="contacto@biblio.gov.co",
            telefono="3001234567",
        )
    ]
    mock_bibliotecas_port.obtener_bibliotecas.return_value = bibliotecas_esperadas

    service = DatosAbiertosService(
        bibliotecas_port=mock_bibliotecas_port,
        divipola_port=mock_divipola_port,
    )

    resultado = service.obtener_bibliotecas(limite=10)

    assert resultado == bibliotecas_esperadas
    mock_bibliotecas_port.obtener_bibliotecas.assert_called_once_with(limite=10)
    mock_divipola_port.obtener_municipios.assert_not_called()


def test_datos_abiertos_service_obtener_municipios():
    mock_bibliotecas_port = MagicMock(spec=BibliotecasPort)
    mock_divipola_port = MagicMock(spec=DivipolaPort)

    municipios_esperados = [
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
    mock_divipola_port.obtener_municipios.return_value = municipios_esperados

    service = DatosAbiertosService(
        bibliotecas_port=mock_bibliotecas_port,
        divipola_port=mock_divipola_port,
    )

    resultado = service.obtener_municipios(limite=25)

    assert resultado == municipios_esperados
    mock_divipola_port.obtener_municipios.assert_called_once_with(limite=25)
    mock_bibliotecas_port.obtener_bibliotecas.assert_not_called()


def test_datos_abiertos_service_propaga_circuito_abierto_error():
    mock_bibliotecas_port = MagicMock(spec=BibliotecasPort)
    mock_divipola_port = MagicMock(spec=DivipolaPort)

    mock_bibliotecas_port.obtener_bibliotecas.side_effect = CircuitoAbiertoError("Circuito ABIERTO")

    service = DatosAbiertosService(
        bibliotecas_port=mock_bibliotecas_port,
        divipola_port=mock_divipola_port,
    )

    with pytest.raises(CircuitoAbiertoError, match="Circuito ABIERTO"):
        service.obtener_bibliotecas(limite=5)


def test_datos_abiertos_service_propaga_fuente_externa_error():
    mock_bibliotecas_port = MagicMock(spec=BibliotecasPort)
    mock_divipola_port = MagicMock(spec=DivipolaPort)

    mock_divipola_port.obtener_municipios.side_effect = FuenteExternaError("Fallo en servicio DANE")

    service = DatosAbiertosService(
        bibliotecas_port=mock_bibliotecas_port,
        divipola_port=mock_divipola_port,
    )

    with pytest.raises(FuenteExternaError, match="Fallo en servicio DANE"):
        service.obtener_municipios(limite=5)
