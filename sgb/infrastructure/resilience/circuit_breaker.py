"""Implementación de Circuit Breaker para resiliencia en infraestructura."""
from enum import Enum
import threading
import time
from typing import Any, Callable, Optional, Tuple, Type

from sgb.domain.exceptions import CircuitoAbiertoError


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int,
        recovery_timeout: float,
        expected_exceptions: Tuple[Type[BaseException], ...],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be greater than 0")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exceptions = expected_exceptions
        self._clock = clock

        self._lock = threading.Lock()
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: Optional[float] = None
        self._half_open_in_progress: bool = False

    @property
    def state(self) -> CircuitState:
        """
        Estado actual del circuito (CLOSED, OPEN o HALF_OPEN).
        Retorna HALF_OPEN en cuanto clock() - instante_apertura >= recovery_timeout,
        incluso si nadie ha llamado a call(). La llamada de prueba consume el permiso de prueba.
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (self._clock() - (self._opened_at or 0.0)) >= self._recovery_timeout:
                    return CircuitState.HALF_OPEN
            return self._state

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (self._clock() - (self._opened_at or 0.0)) >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_in_progress = False

            if self._state == CircuitState.OPEN:
                raise CircuitoAbiertoError("El circuito está ABIERTO")

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_in_progress:
                    raise CircuitoAbiertoError("El circuito está en prueba (HALF_OPEN)")
                self._half_open_in_progress = True
                is_trial = True
            else:
                is_trial = False

        trial_completed = False
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                trial_completed = True
                if is_trial:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._opened_at = None
                    self._half_open_in_progress = False
                else:
                    if self._state == CircuitState.CLOSED:
                        self._failure_count = 0
            return result
        except self._expected_exceptions:
            with self._lock:
                trial_completed = True
                if is_trial:
                    self._state = CircuitState.OPEN
                    self._opened_at = self._clock()
                    self._half_open_in_progress = False
                else:
                    if self._state == CircuitState.CLOSED:
                        self._failure_count += 1
                        if self._failure_count >= self._failure_threshold:
                            self._state = CircuitState.OPEN
                            self._opened_at = self._clock()
            raise
        finally:
            if is_trial and not trial_completed:
                with self._lock:
                    self._half_open_in_progress = False
                    self._state = CircuitState.HALF_OPEN
