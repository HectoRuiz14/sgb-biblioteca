"""Pruebas unitarias para componentes de resiliencia (CircuitBreaker y retry_con_backoff)."""
from unittest.mock import MagicMock
import pytest

from sgb.domain.exceptions import CircuitoAbiertoError
from sgb.infrastructure.resilience import (
    CircuitBreaker,
    CircuitState,
    retry_con_backoff,
)


class FakeClock:
    def __init__(self, initial: float = 1000.0):
        self.current = initial

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class FakeSleep:
    def __init__(self):
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


# ==========================================
# Tests de CircuitBreaker
# ==========================================

@pytest.mark.parametrize(
    "threshold,timeout",
    [
        (0, 10.0),
        (-1, 10.0),
        (3, 0.0),
        (3, -1.0),
    ],
)
def test_circuit_breaker_validaciones_constructor_parametrizadas(threshold, timeout):
    with pytest.raises(ValueError):
        CircuitBreaker(
            failure_threshold=threshold,
            recovery_timeout=timeout,
            expected_exceptions=(Exception,),
        )


def test_circuit_breaker_closed_a_open_exactamente_en_umbral():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    def failing_call():
        raise ValueError("falla")

    # 1er fallo -> CLOSED
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED

    # 2do fallo -> CLOSED
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED

    # 3er fallo (alcanza el umbral) -> OPEN
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_exito_en_closed_reinicia_contador_fallos():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    def failing_call():
        raise ValueError("falla")

    # 2 fallos consecutivos
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED

    # Éxito intermedio -> reinicia el contador a 0
    res = breaker.call(lambda: "ok")
    assert res == "ok"
    assert breaker.state == CircuitState.CLOSED

    # Otros 2 fallos no deben abrir el circuito
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_open_rechaza_con_circuito_abierto_sin_llamar_fn():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(RuntimeError,),
        clock=clock,
    )

    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("error inicial")))

    assert breaker.state == CircuitState.OPEN

    fn = MagicMock()
    with pytest.raises(CircuitoAbiertoError):
        breaker.call(fn)

    fn.assert_not_called()


def test_circuit_breaker_open_a_half_open_al_cumplirse_recovery_timeout_y_no_antes():
    clock = FakeClock(initial=100.0)
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError()))

    assert breaker.state == CircuitState.OPEN

    # Un instante antes de recovery_timeout (9.99s)
    clock.advance(9.99)
    assert breaker.state == CircuitState.OPEN

    # Exactamente en recovery_timeout (10.0s)
    clock.advance(0.01)
    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_half_open_a_closed_si_prueba_exitosa():
    clock = FakeClock(initial=100.0)
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError()))

    # Avanzar a HALF_OPEN
    clock.advance(10.0)
    assert breaker.state == CircuitState.HALF_OPEN

    # Llamada de prueba exitosa
    resultado = breaker.call(lambda: "recuperado")
    assert resultado == "recuperado"
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_a_open_si_prueba_falla_reinicia_temporizador():
    clock = FakeClock(initial=100.0)
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    # Abre el circuito en t=100.0
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError()))

    # Avanza a t=110.0 (HALF_OPEN)
    clock.advance(10.0)
    assert breaker.state == CircuitState.HALF_OPEN

    # Llamada de prueba falla en t=110.0 -> regresa a OPEN y reinicia temporizador
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("falla prueba")))

    assert breaker.state == CircuitState.OPEN

    # Avanza 5s hasta t=115.0 -> debe seguir OPEN porque el nuevo timeout vence en t=120.0
    clock.advance(5.0)
    assert breaker.state == CircuitState.OPEN

    # Avanza 5s más hasta t=120.0 -> pasa a HALF_OPEN
    clock.advance(5.0)
    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_half_open_solo_permite_una_llamada_de_prueba():
    clock = FakeClock(initial=100.0)
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(ValueError,),
        clock=clock,
    )

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError()))

    clock.advance(10.0)
    assert breaker.state == CircuitState.HALF_OPEN

    def prueba_reentrante():
        # Mientras esta llamada de prueba está en curso, otra llamada recibe CircuitoAbiertoError
        with pytest.raises(CircuitoAbiertoError):
            breaker.call(lambda: "otra llamada")
        return "prueba_ok"

    res = breaker.call(prueba_reentrante)
    assert res == "prueba_ok"
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_excepcion_inesperada_libera_permiso_y_mantiene_half_open():
    clock = FakeClock(initial=100.0)
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10.0,
        expected_exceptions=(KeyError,),
        clock=clock,
    )

    with pytest.raises(KeyError):
        breaker.call(lambda: (_ for _ in ()).throw(KeyError()))

    clock.advance(10.0)
    assert breaker.state == CircuitState.HALF_OPEN

    # La prueba lanza TypeError (fuera de expected_exceptions)
    with pytest.raises(TypeError):
        breaker.call(lambda: (_ for _ in ()).throw(TypeError("inesperada")))

    # El estado debe seguir en HALF_OPEN y el permiso liberado para la siguiente prueba
    assert breaker.state == CircuitState.HALF_OPEN

    # La siguiente llamada debe poder ejecutarse como prueba y cerrar el circuito
    res = breaker.call(lambda: "nueva_prueba")
    assert res == "nueva_prueba"
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_excepcion_fuera_de_expected_exceptions_no_cuenta_como_fallo():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10.0,
        expected_exceptions=(KeyError,),
        clock=clock,
    )

    # TypeError no está en expected_exceptions -> se propaga sin sumar fallos
    with pytest.raises(TypeError):
        breaker.call(lambda: (_ for _ in ()).throw(TypeError("ajena")))

    with pytest.raises(TypeError):
        breaker.call(lambda: (_ for _ in ()).throw(TypeError("ajena 2")))

    assert breaker.state == CircuitState.CLOSED


# ==========================================
# Tests de retry_con_backoff
# ==========================================

def test_retry_validacion_attempts_menor_a_uno():
    with pytest.raises(ValueError, match="attempts must be at least 1"):
        retry_con_backoff(
            lambda: "ok",
            attempts=0,
            base_delay=1.0,
            factor=2.0,
            max_delay=10.0,
            retry_on=(Exception,),
        )


def test_retry_secuencia_esperas_verificada_con_sleep_falso():
    sleep = FakeSleep()
    contador = {"intentos": 0}

    def fn():
        contador["intentos"] += 1
        raise ValueError("falla")

    with pytest.raises(ValueError):
        retry_con_backoff(
            fn,
            attempts=4,
            base_delay=1.0,
            factor=2.0,
            max_delay=10.0,
            retry_on=(ValueError,),
            sleep=sleep,
        )

    assert contador["intentos"] == 4
    # Esperas antes de intento 2, 3 y 4: 1.0, 2.0, 4.0
    assert sleep.calls == [1.0, 2.0, 4.0]


def test_retry_respeta_max_delay():
    sleep = FakeSleep()

    def fn():
        raise RuntimeError("error")

    with pytest.raises(RuntimeError):
        retry_con_backoff(
            fn,
            attempts=4,
            base_delay=2.0,
            factor=3.0,
            max_delay=5.0,
            retry_on=(RuntimeError,),
            sleep=sleep,
        )

    # Teóricas: [2.0, 6.0, 18.0] -> truncadas por max_delay=5.0: [2.0, 5.0, 5.0]
    assert sleep.calls == [2.0, 5.0, 5.0]


def test_retry_sin_sleep_tras_ultimo_intento():
    sleep = FakeSleep()

    def fn():
        raise KeyError("clave")

    with pytest.raises(KeyError):
        retry_con_backoff(
            fn,
            attempts=3,
            base_delay=1.0,
            factor=2.0,
            max_delay=10.0,
            retry_on=(KeyError,),
            sleep=sleep,
        )

    # 3 intentos -> exactamente 2 esperas (no duerme tras el 3er intento)
    assert len(sleep.calls) == 2


def test_retry_excepcion_no_reintentable_se_propaga_sin_reintentos():
    sleep = FakeSleep()
    contador = {"intentos": 0}

    def fn():
        contador["intentos"] += 1
        raise TypeError("no reintentable")

    with pytest.raises(TypeError):
        retry_con_backoff(
            fn,
            attempts=5,
            base_delay=1.0,
            factor=2.0,
            max_delay=10.0,
            retry_on=(ValueError,),
            sleep=sleep,
        )

    assert contador["intentos"] == 1
    assert sleep.calls == []


def test_retry_exito_en_primer_intento_no_duerme():
    sleep = FakeSleep()
    res = retry_con_backoff(
        lambda: 42,
        attempts=3,
        base_delay=1.0,
        factor=2.0,
        max_delay=10.0,
        retry_on=(Exception,),
        sleep=sleep,
    )
    assert res == 42
    assert sleep.calls == []


def test_composicion_retry_dentro_de_breaker_cuenta_como_un_solo_fallo():
    clock = FakeClock()
    sleep = FakeSleep()

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10.0,
        expected_exceptions=(RuntimeError,),
        clock=clock,
    )

    def llamada_externa():
        raise RuntimeError("servicio caido")

    def operacion_con_retry():
        return retry_con_backoff(
            llamada_externa,
            attempts=3,
            base_delay=1.0,
            factor=2.0,
            max_delay=5.0,
            retry_on=(RuntimeError,),
            sleep=sleep,
        )

    # 1er llamado a breaker: retry falla sus 3 intentos, pero cuenta como 1 solo fallo para el breaker
    with pytest.raises(RuntimeError):
        breaker.call(operacion_con_retry)

    assert len(sleep.calls) == 2
    assert breaker.state == CircuitState.CLOSED

    # 2do llamado a breaker: retry vuelve a fallar -> 2do fallo en breaker -> transiciona a OPEN
    with pytest.raises(RuntimeError):
        breaker.call(operacion_con_retry)

    assert len(sleep.calls) == 4
    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_exito_tardio_no_cierra_circuito_abierto():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10.0,
        expected_exceptions=(RuntimeError,),
        clock=clock,
    )

    def llamada_A():
        def fallar():
            raise RuntimeError("fallo")

        with pytest.raises(RuntimeError):
            breaker.call(fallar)
        with pytest.raises(RuntimeError):
            breaker.call(fallar)
        assert breaker.state == CircuitState.OPEN
        return "valor_A"

    res = breaker.call(llamada_A)
    assert res == "valor_A"
    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_fallo_tardio_no_reinicia_temporizador():
    clock = FakeClock(initial=1000.0)
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10.0,
        expected_exceptions=(RuntimeError,),
        clock=clock,
    )

    def llamada_A():
        def fallar():
            raise RuntimeError("fallo")

        with pytest.raises(RuntimeError):
            breaker.call(fallar)
        with pytest.raises(RuntimeError):
            breaker.call(fallar)
        assert breaker.state == CircuitState.OPEN
        clock.advance(9.0)
        raise RuntimeError("fallo tardio de A")

    with pytest.raises(RuntimeError, match="fallo tardio de A"):
        breaker.call(llamada_A)

    clock.advance(1.0)
    assert breaker.state == CircuitState.HALF_OPEN

