"""Pruebas unitarias para DuckDBAnalisisAdapter usando DuckDB en memoria."""
import pytest
import duckdb

from sgb.domain.datos_abiertos.entities import (
    BibliotecaPublica,
    CruceDivipolaResultado,
    EstadisticasBibliotecas,
    MunicipioDivipola,
)
from sgb.infrastructure.datos_abiertos.duckdb_adapter import (
    DuckDBAnalisisAdapter,
    normalizar_municipio,
)


BIBLIOTECAS_MOCK = [
    BibliotecaPublica(nombre="Biblio 1", municipio="Bucaramanga", correo="b1@santander.gov.co"),
    BibliotecaPublica(nombre="Biblio 2", municipio="Bucaramanga", correo=None),
    BibliotecaPublica(nombre="Biblio 3", municipio="Floridablanca", correo="b3@santander.gov.co"),
    BibliotecaPublica(nombre="Biblio 4", municipio="Girón", correo="b4@santander.gov.co"),
]

DIVIPOLA_MOCK = [
    MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68001",
                      municipio="BUCARAMANGA", tipo="Municipio", longitud="-73,1198", latitud="7,1253"),
    MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68276",
                      municipio="FLORIDABLANCA", tipo="Municipio", longitud="-73,0864", latitud="7,0622"),
    MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68307",
                      municipio="GIRON", tipo="Municipio", longitud="-73,1698", latitud="7,0733"),
    MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68895",
                      municipio="ZAPATOCA", tipo="Municipio", longitud="-73,2711", latitud="6,8150"),
    MunicipioDivipola(codigo_departamento="05", departamento="ANTIOQUIA", codigo_municipio="05001",
                      municipio="MEDELLIN", tipo="Municipio", longitud="-75,5818", latitud="6,2466"),
]


@pytest.fixture
def adapter():
    con = duckdb.connect(":memory:")
    return DuckDBAnalisisAdapter(connection=con)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("BOGOTÁ, D.C.", "BOGOTA, D.C."),
        ("Medellín", "MEDELLIN"),
        ("Girón", "GIRON"),
        ("  san vicente de chucurí  ", "SAN VICENTE DE CHUCURI"),
        ("", ""),
    ],
)
def test_normalizar_municipio(entrada, esperado):
    assert normalizar_municipio(entrada) == esperado


def test_analizar_bibliotecas_calcula_estadisticas_correctas(adapter):
    resultado = adapter.analizar_bibliotecas(BIBLIOTECAS_MOCK)

    assert isinstance(resultado, EstadisticasBibliotecas)
    assert resultado.total_bibliotecas == 4
    assert resultado.total_municipios_con_biblioteca == 3
    assert resultado.porcentaje_con_correo == 75.0
    assert len(resultado.top_municipios) == 3

    top_1 = resultado.top_municipios[0]
    assert top_1.municipio == "BUCARAMANGA"
    assert top_1.total_bibliotecas == 2


def test_analizar_bibliotecas_lista_vacia(adapter):
    resultado = adapter.analizar_bibliotecas([])

    assert resultado.total_bibliotecas == 0
    assert resultado.total_municipios_con_biblioteca == 0
    assert resultado.porcentaje_con_correo == 0.0
    assert resultado.top_municipios == []


def test_cruzar_con_divipola_filtra_solo_departamentos_cubiertos(adapter):
    resultado = adapter.cruzar_con_divipola(BIBLIOTECAS_MOCK, DIVIPOLA_MOCK)

    assert isinstance(resultado, CruceDivipolaResultado)
    # Antioquia no tiene bibliotecas en BIBLIOTECAS_MOCK, por lo que se filtra. Solo se evalúan los 4 de Santander.
    assert resultado.total_municipios_divipola == 4
    # Solo Zapatoca (Santander) no tiene biblioteca
    assert resultado.municipios_sin_biblioteca == 1

    # Estadísticas descriptivas de cant_bib sobre los 4 municipios de Santander: [2, 1, 1, 0]
    stats = resultado.estadisticas_distribucion
    assert stats.media == 1.0
    assert stats.mediana == 1.0
    assert stats.minimo == 0
    assert stats.maximo == 2

    # Solo aparece el departamento con presencia de bibliotecas
    deptos = {d.departamento: d.total_bibliotecas for d in resultado.bibliotecas_por_departamento}
    assert deptos == {"SANTANDER": 4}
    assert "ANTIOQUIA" not in deptos


def test_cruzar_con_divipola_dos_departamentos_excluye_no_cubiertos(adapter):
    bibliotecas = [
        BibliotecaPublica(nombre="Biblio Bucaramanga", municipio="Bucaramanga"),
        BibliotecaPublica(nombre="Biblio Medellin 1", municipio="Medellín"),
        BibliotecaPublica(nombre="Biblio Medellin 2", municipio="Medellín"),
    ]
    municipios = [
        # Santander
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68001", municipio="BUCARAMANGA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68895", municipio="ZAPATOCA", tipo="Municipio"),
        # Antioquia
        MunicipioDivipola(codigo_departamento="05", departamento="ANTIOQUIA", codigo_municipio="05001", municipio="MEDELLIN", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="05", departamento="ANTIOQUIA", codigo_municipio="05002", municipio="ABEJORRAL", tipo="Municipio"),
        # Boyacá (no tiene bibliotecas en el dataset, debe ser excluido del alcance)
        MunicipioDivipola(codigo_departamento="15", departamento="BOYACA", codigo_municipio="15001", municipio="TUNJA", tipo="Municipio"),
    ]

    res = adapter.cruzar_con_divipola(bibliotecas, municipios)

    # Solo se evalúan Santander (2 mpios) y Antioquia (2 mpios) = 4 municipios en total. Boyacá se excluye.
    assert res.total_municipios_divipola == 4
    # Zapatoca (Santander) y Abejorral (Antioquia) no tienen biblioteca -> 2
    assert res.municipios_sin_biblioteca == 2

    deptos = {d.departamento: d.total_bibliotecas for d in res.bibliotecas_por_departamento}
    assert deptos == {"ANTIOQUIA": 2, "SANTANDER": 1}
    assert "BOYACA" not in deptos

    # Distribución sobre [1, 0, 2, 0]:
    # Media: (1 + 0 + 2 + 0) / 4 = 0.75
    # Mediana: [0, 0, 1, 2] -> 0.5
    assert res.estadisticas_distribucion.media == 0.75
    assert res.estadisticas_distribucion.mediana == 0.5
    assert res.estadisticas_distribucion.minimo == 0
    assert res.estadisticas_distribucion.maximo == 2


def test_cruzar_con_divipola_municipio_homonimo_excluye_departamento_espurio_y_no_duplica(adapter):
    """Verifica que municipios homónimos no cuelen departamentos espurios ni dupliquen bibliotecas."""
    bibliotecas = [
        BibliotecaPublica(nombre="Biblio Bga 1", municipio="Bucaramanga"),
        BibliotecaPublica(nombre="Biblio Bga 2", municipio="Bucaramanga"),
        BibliotecaPublica(nombre="Biblio Florida", municipio="Floridablanca"),
        BibliotecaPublica(nombre="Biblio Girón", municipio="Girón"),
        BibliotecaPublica(nombre="Biblio Cabrera", municipio="Cabrera"),
    ]
    municipios = [
        # Santander (4 coincidencias distintas con el dataset de bibliotecas)
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68001", municipio="BUCARAMANGA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68276", municipio="FLORIDABLANCA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68307", municipio="GIRON", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68121", municipio="CABRERA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="68", departamento="SANTANDER", codigo_municipio="68895", municipio="ZAPATOCA", tipo="Municipio"),
        # Cundinamarca (solo 1 coincidencia por el homónimo "CABRERA", <= 50% de 4 coincidencias)
        MunicipioDivipola(codigo_departamento="25", departamento="CUNDINAMARCA", codigo_municipio="25120", municipio="CABRERA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="25", departamento="CUNDINAMARCA", codigo_municipio="25001", municipio="BOGOTA", tipo="Municipio"),
        MunicipioDivipola(codigo_departamento="25", departamento="CUNDINAMARCA", codigo_municipio="25754", municipio="SOACHA", tipo="Municipio"),
    ]

    res = adapter.cruzar_con_divipola(bibliotecas, municipios)

    # 1. Cundinamarca debe ser descartado (1 coincidencia <= 50% del máximo de 4). Solo Santander entra.
    assert res.total_municipios_divipola == 5
    # 2. Solo Zapatoca (Santander) no tiene biblioteca
    assert res.municipios_sin_biblioteca == 1

    # 3. El total de bibliotecas no debe duplicarse por el homónimo Cabrera (exactamente 5 bibliotecas)
    deptos = {d.departamento: d.total_bibliotecas for d in res.bibliotecas_por_departamento}
    assert deptos == {"SANTANDER": 5}
    assert "CUNDINAMARCA" not in deptos
    assert sum(d.total_bibliotecas for d in res.bibliotecas_por_departamento) == len(bibliotecas)

    # 4. Estadísticas descriptivas sobre Santander [2, 1, 1, 1, 0]:
    # Media: 5 / 5 = 1.0, Mediana: 1.0, Min: 0, Max: 2
    assert res.estadisticas_distribucion.media == 1.0
    assert res.estadisticas_distribucion.mediana == 1.0
    assert res.estadisticas_distribucion.minimo == 0
    assert res.estadisticas_distribucion.maximo == 2


def test_cruzar_con_divipola_listas_vacias(adapter):
    resultado = adapter.cruzar_con_divipola([], [])

    assert resultado.total_municipios_divipola == 0
    assert resultado.municipios_sin_biblioteca == 0
    assert resultado.estadisticas_distribucion.media == 0.0

