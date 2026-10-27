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


# ---------------------------------------------------------------------------
# Helpers y Fakes reutilizables
# ---------------------------------------------------------------------------

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


def _make_request() -> httpx.Request:
    return httpx.Request("GET", "https://api.test")


def _make_conn_err(req: httpx.Request, msg: str = "falla red") -> httpx.ConnectError:
    return httpx.ConnectError(msg, request=req)


def _make_adapter(adapter_cls, *, client, sleep=None, clock=None, breaker=None,
                  retry_attempts=3, base_delay=0.5):
    """Factoría para construir un adaptador con los fakes inyectados."""
    kwargs = dict(client=client, retry_attempts=retry_attempts, base_delay=base_delay)
    if sleep is not None:
        kwargs["sleep"] = sleep
    if clock is not None:
        kwargs["clock"] = clock
    if breaker is not None:
        kwargs["breaker"] = breaker
    return adapter_cls(**kwargs)


def _call_adapter(adapter, limite=5):
    """Invoca el método público del adaptador según su tipo."""
    if isinstance(adapter, BibliotecasDatosGovAdapter):
        return adapter.obtener_bibliotecas(limite=limite)
    return adapter.obtener_municipios(limite=limite)


# ---------------------------------------------------------------------------
# Datos verificados de los endpoints reales
# ---------------------------------------------------------------------------

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

ADAPTER_DATASET = {
    BibliotecasDatosGovAdapter: VERIFIED_BIBLIOTECAS_JSON,
    DaneDivipolaAdapter: VERIFIED_DIVIPOLA_JSON,
}


# ---------------------------------------------------------------------------
# Test unificado de éxito con JSON verificado (parametrizado)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "adapter_cls,payload,expected_cls,expected_fields",
    [
        (
            BibliotecasDatosGovAdapter,
            VERIFIED_BIBLIOTECAS_JSON,
            BibliotecaPublica,
            {"nombre": "Biblioteca Pública Municipal Alvaro Ruiz Arenas", "municipio": "Contratacion"},
        ),
        (
            DaneDivipolaAdapter,
            VERIFIED_DIVIPOLA_JSON,
            MunicipioDivipola,
            {"codigo_municipio": "05001", "municipio": "MEDELLÍN"},
        ),
    ],
)
def test_adapter_exito_con_json_verificado(adapter_cls, payload, expected_cls, expected_fields):
    client = FakeHttpClient([FakeResponse(200, payload)])
    adapter = adapter_cls(client=client)

    items = _call_adapter(adapter, limite=2)

    assert len(items) == 2
    assert isinstance(items[0], expected_cls)
    for k, v in expected_fields.items():
        assert getattr(items[0], k) == v
    assert client.calls[0]["params"] == {"$limit": "2"}


# ---------------------------------------------------------------------------
# Tests parametrizados para escenarios comunes a ambos adaptadores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_reintento_que_termina_en_exito(adapter_cls):
    sleep = FakeSleep()
    json_data = ADAPTER_DATASET[adapter_cls]
    client = FakeHttpClient([
        FakeResponse(500, text="Internal Server Error"),
        FakeResponse(429, text="Too Many Requests"),
        FakeResponse(200, json_data),
    ])
    adapter = _make_adapter(adapter_cls, client=client, sleep=sleep,
                            retry_attempts=3, base_delay=1.0)

    resultado = _call_adapter(adapter, limite=5)

    assert len(resultado) == 2
    assert len(client.calls) == 3
    assert sleep.calls == [1.0, 2.0]
    assert adapter.breaker.state == CircuitState.CLOSED


@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_retry_agotado_lanza_fuente_externa_error(adapter_cls):
    sleep = FakeSleep()
    req = _make_request()
    client = FakeHttpClient([_make_conn_err(req, f"Fallo {i}") for i in (1, 2, 3)])
    adapter = _make_adapter(adapter_cls, client=client, sleep=sleep,
                            retry_attempts=3, base_delay=1.0)

    with pytest.raises(FuenteExternaError, match="Error al consultar"):
        _call_adapter(adapter, limite=5)

    assert len(client.calls) == 3
    assert len(sleep.calls) == 2


@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_breaker_pasa_a_open_y_rechaza(adapter_cls):
    clock = FakeClock()
    sleep = FakeSleep()
    req = _make_request()
    json_data = ADAPTER_DATASET[adapter_cls]

    breaker = CircuitBreaker(
        failure_threshold=2, recovery_timeout=30.0,
        expected_exceptions=(httpx.RequestError, Exception), clock=clock,
    )
    # 3 fallos para intento 1 + 3 fallos para intento 2 + respuesta 200 no alcanzada
    client = FakeHttpClient([_make_conn_err(req) for _ in range(6)] + [FakeResponse(200, json_data)])
    adapter = _make_adapter(adapter_cls, client=client, breaker=breaker,
                            sleep=sleep, clock=clock, retry_attempts=3, base_delay=0.1)

    with pytest.raises(FuenteExternaError):
        _call_adapter(adapter)
    assert adapter.breaker.state == CircuitState.CLOSED

    with pytest.raises(FuenteExternaError):
        _call_adapter(adapter)
    assert adapter.breaker.state == CircuitState.OPEN

    llamadas_previas = len(client.calls)
    with pytest.raises(CircuitoAbiertoError):
        _call_adapter(adapter)
    assert len(client.calls) == llamadas_previas


@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_paso_a_half_open_tras_recovery_timeout(adapter_cls):
    clock = FakeClock(initial=1000.0)
    sleep = FakeSleep()
    req = _make_request()
    json_data = ADAPTER_DATASET[adapter_cls]

    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=15.0,
        expected_exceptions=(httpx.RequestError, Exception), clock=clock,
    )
    client = FakeHttpClient([_make_conn_err(req), FakeResponse(200, json_data)])
    adapter = _make_adapter(adapter_cls, client=client, breaker=breaker,
                            sleep=sleep, clock=clock, retry_attempts=1)

    with pytest.raises(FuenteExternaError):
        _call_adapter(adapter)
    assert adapter.breaker.state == CircuitState.OPEN

    clock.advance(14.9)
    assert adapter.breaker.state == CircuitState.OPEN

    clock.advance(0.1)
    assert adapter.breaker.state == CircuitState.HALF_OPEN

    res = _call_adapter(adapter, limite=2)
    assert len(res) == 2
    assert adapter.breaker.state == CircuitState.CLOSED


@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_json_invalido_lanza_fuente_externa_error_sin_reintentar(adapter_cls):
    sleep = FakeSleep()
    client = FakeHttpClient([FakeResponse(200, {"mensaje": "no es una lista"})])
    adapter = _make_adapter(adapter_cls, client=client, sleep=sleep, retry_attempts=3)

    with pytest.raises(FuenteExternaError, match="Respuesta de la fuente no es una lista"):
        _call_adapter(adapter)

    assert len(client.calls) == 1
    assert sleep.calls == []


@pytest.mark.parametrize("adapter_cls", [BibliotecasDatosGovAdapter, DaneDivipolaAdapter])
def test_adapter_error_http_4xx_no_reintenta(adapter_cls):
    sleep = FakeSleep()
    client = FakeHttpClient([FakeResponse(404, text="Recurso no encontrado")])
    adapter = _make_adapter(adapter_cls, client=client, sleep=sleep, retry_attempts=3)

    with pytest.raises(FuenteExternaError, match="Error cliente HTTP 404"):
        _call_adapter(adapter)

    assert len(client.calls) == 1
    assert sleep.calls == []
