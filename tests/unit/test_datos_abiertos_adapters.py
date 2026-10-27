"""Pruebas unitarias para los adaptadores de datos abiertos con CircuitBreaker y retry."""
from typing import Any, List
import httpx
import pytest

from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError
from sgb.infrastructure.datos_abiertos.adapters import (
    BibliotecasDatosGovAdapter,
    DaneDivipolaAdapter,
)
from sgb.infrastructure.resilience import CircuitBreaker, CircuitState


class FakeClock:
    def __init__(self, initial: float = 1000.0):
        self.current = initial

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class FakeSleep:
    def __init__(self):
        self.calls: List[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class FakeResponse:
    def __init__(self, status_code: int, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or str(json_data)

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FakeHttpClient:
    def __init__(self, responses: List[Any]):
        self.responses = list(responses)
        self.calls: List[dict] = []

    def get(self, url: str, params: dict = None, timeout: float = None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if not self.responses:
            raise RuntimeError("No hay más respuestas simuladas en FakeHttpClient")
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


VERIFIED_BIBLIOTECAS_JSON = [
    {
        "no": "Yuri Mabel Sanchez Gutierrez",
        "municipio": "Contratacion",
        "nombre_de_la_biblioteca": "Biblioteca Pública Municipal Alvaro Ruiz Arenas",
        "celular_de_contacto_del": "3123380841",
        "correo_electronico": "yurisanchezgutierrez1306@gmail.com",
        "mod_contra": "CPS",
    },
    {
        "no": "Adriana Marcela Martinez Cristancho",
        "municipio": "Cabrera",
        "nombre_de_la_biblioteca": "Biblioteca Pública Municipal Domingo Carvajal Calderón",
        "celular_de_contacto_del": "3017915341",
        "correo_electronico": "bibpublica.cabrera@gmail.com",
        "mod_contra": "Carrera Administrativa",
    },
]

VERIFIED_DIVIPOLA_JSON = [
    {
        "cod_dpto": "05",
        "dpto": "ANTIOQUIA",
        "cod_mpio": "05001",
        "nom_mpio": "MEDELLÍN",
        "tipo_municipio": "Municipio",
        "longitud": "-75,581775",
        "latitud": "6,246631",
    },
    {
        "cod_dpto": "05",
        "dpto": "ANTIOQUIA",
        "cod_mpio": "05002",
        "nom_mpio": "ABEJORRAL",
        "tipo_municipio": "Municipio",
        "longitud": "-75,428739",
        "latitud": "5,789315",
    },
]


def test_bibliotecas_adapter_exito_con_json_verificado():
    client = FakeHttpClient([FakeResponse(200, VERIFIED_BIBLIOTECAS_JSON)])
    adapter = BibliotecasDatosGovAdapter(client=client)

    bibliotecas = adapter.obtener_bibliotecas(limite=2)

    assert len(bibliotecas) == 2
    assert isinstance(bibliotecas[0], BibliotecaPublica)
    assert bibliotecas[0].nombre == "Biblioteca Pública Municipal Alvaro Ruiz Arenas"
    assert bibliotecas[0].municipio == "Contratacion"
    assert bibliotecas[0].correo == "yurisanchezgutierrez1306@gmail.com"
    assert bibliotecas[0].telefono == "3123380841"
    assert client.calls[0]["params"] == {"$limit": "2"}


def test_divipola_adapter_exito_con_json_verificado():
    client = FakeHttpClient([FakeResponse(200, VERIFIED_DIVIPOLA_JSON)])
    adapter = DaneDivipolaAdapter(client=client)

    municipios = adapter.obtener_municipios(limite=2)

    assert len(municipios) == 2
    assert isinstance(municipios[0], MunicipioDivipola)
    assert municipios[0].codigo_municipio == "05001"
    assert municipios[0].municipio == "MEDELLÍN"
    assert municipios[0].codigo_departamento == "05"
    assert municipios[0].departamento == "ANTIOQUIA"
    assert municipios[0].longitud == "-75,581775"
    assert municipios[0].latitud == "6,246631"


def test_adapter_reintento_que_termina_en_exito():
    sleep = FakeSleep()
    # 500 (reintentable), 429 (reintentable), luego 200 (éxito)
    client = FakeHttpClient([
        FakeResponse(500, text="Internal Server Error"),
        FakeResponse(429, text="Too Many Requests"),
        FakeResponse(200, VERIFIED_BIBLIOTECAS_JSON),
    ])
    adapter = BibliotecasDatosGovAdapter(
        client=client,
        retry_attempts=3,
        base_delay=1.0,
        factor=2.0,
        sleep=sleep,
    )

    resultado = adapter.obtener_bibliotecas(limite=5)

    assert len(resultado) == 2
    assert len(client.calls) == 3
    # Esperas registradas antes de intento 2 y 3: [1.0, 2.0]
    assert sleep.calls == [1.0, 2.0]
    assert adapter.breaker.state == CircuitState.CLOSED


def test_adapter_retry_agotado_lanza_fuente_externa_error():
    sleep = FakeSleep()
    request = httpx.Request("GET", "https://api.test")
    # 3 fallos consecutivos de red agotan los 3 intentos
    client = FakeHttpClient([
        httpx.ConnectError("Fallo de conexion 1", request=request),
        httpx.ConnectError("Fallo de conexion 2", request=request),
        httpx.ConnectError("Fallo de conexion 3", request=request),
    ])
    adapter = BibliotecasDatosGovAdapter(
        client=client,
        retry_attempts=3,
        base_delay=1.0,
        factor=2.0,
        sleep=sleep,
    )

    with pytest.raises(FuenteExternaError, match="Error al consultar fuente de bibliotecas"):
        adapter.obtener_bibliotecas(limite=5)

    assert len(client.calls) == 3
    assert len(sleep.calls) == 2


def test_adapter_breaker_pasa_a_open_tras_n_fallos_y_rechaza_con_circuito_abierto():
    clock = FakeClock()
    sleep = FakeSleep()
    request = httpx.Request("GET", "https://api.test")

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=30.0,
        expected_exceptions=(httpx.RequestError, Exception),
        clock=clock,
    )
    client = FakeHttpClient([
        # Fallo 1 (3 reintentos)
        httpx.ConnectError("falla red 1", request=request),
        httpx.ConnectError("falla red 1", request=request),
        httpx.ConnectError("falla red 1", request=request),
        # Fallo 2 (3 reintentos) -> abre el breaker
        httpx.ConnectError("falla red 2", request=request),
        httpx.ConnectError("falla red 2", request=request),
        httpx.ConnectError("falla red 2", request=request),
        # Si se llamara en la 3ra daría 200, pero el breaker debe rechazarla sin llamar
        FakeResponse(200, VERIFIED_DIVIPOLA_JSON),
    ])
    adapter = DaneDivipolaAdapter(
        client=client,
        breaker=breaker,
        retry_attempts=3,
        base_delay=0.1,
        sleep=sleep,
        clock=clock,
    )

    # 1er fallo
    with pytest.raises(FuenteExternaError):
        adapter.obtener_municipios(limite=5)
    assert adapter.breaker.state == CircuitState.CLOSED

    # 2do fallo -> pasa a OPEN
    with pytest.raises(FuenteExternaError):
        adapter.obtener_municipios(limite=5)
    assert adapter.breaker.state == CircuitState.OPEN

    # 3er intento -> rechazado inmediatamente por CircuitoAbiertoError sin llamar al cliente
    llamadas_previas = len(client.calls)
    with pytest.raises(CircuitoAbiertoError):
        adapter.obtener_municipios(limite=5)

    assert len(client.calls) == llamadas_previas


def test_adapter_paso_a_half_open_tras_recovery_timeout():
    clock = FakeClock(initial=1000.0)
    sleep = FakeSleep()
    request = httpx.Request("GET", "https://api.test")

    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=15.0,
        expected_exceptions=(httpx.RequestError, Exception),
        clock=clock,
    )
    client = FakeHttpClient([
        # Abre el circuito
        httpx.ConnectError("falla", request=request),
        # Respuesta exitosa de prueba
        FakeResponse(200, VERIFIED_BIBLIOTECAS_JSON),
    ])
    adapter = BibliotecasDatosGovAdapter(
        client=client,
        breaker=breaker,
        retry_attempts=1,
        sleep=sleep,
        clock=clock,
    )

    with pytest.raises(FuenteExternaError):
        adapter.obtener_bibliotecas(limite=5)
    assert adapter.breaker.state == CircuitState.OPEN

    # Antes del timeout (14.9s)
    clock.advance(14.9)
    assert adapter.breaker.state == CircuitState.OPEN

    # Al cumplirse el timeout (15.0s) -> HALF_OPEN
    clock.advance(0.1)
    assert adapter.breaker.state == CircuitState.HALF_OPEN

    # Llamada de prueba exitosa -> transiciona a CLOSED
    res = adapter.obtener_bibliotecas(limite=2)
    assert len(res) == 2
    assert adapter.breaker.state == CircuitState.CLOSED


def test_adapter_json_invalido_lanza_fuente_externa_error_sin_reintentar():
    sleep = FakeSleep()
    # JSON que no es lista
    client = FakeHttpClient([FakeResponse(200, {"mensaje": "no es una lista"})])
    adapter = BibliotecasDatosGovAdapter(client=client, retry_attempts=3, sleep=sleep)

    with pytest.raises(FuenteExternaError, match="Respuesta de la fuente no es una lista"):
        adapter.obtener_bibliotecas()

    # Errores de formato no deben reintentarse
    assert len(client.calls) == 1
    assert sleep.calls == []


def test_adapter_error_http_4xx_no_reintenta():
    sleep = FakeSleep()
    # 404 Not Found
    client = FakeHttpClient([FakeResponse(404, text="Recurso no encontrado")])
    adapter = DaneDivipolaAdapter(client=client, retry_attempts=3, sleep=sleep)

    with pytest.raises(FuenteExternaError, match="Error cliente HTTP 404"):
        adapter.obtener_municipios()

    # 4xx no se reintenta
    assert len(client.calls) == 1
    assert sleep.calls == []
