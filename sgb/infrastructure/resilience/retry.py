"""Implementación de reintentos con retroceso exponencial."""
import time
from typing import Any, Callable, Tuple, Type


def retry_con_backoff(
    fn: Callable[[], Any],
    *,
    attempts: int,
    base_delay: float,
    factor: float,
    max_delay: float,
    retry_on: Tuple[Type[BaseException], ...],
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """
    Ejecuta un callable sin argumentos con reintentos y retroceso exponencial.
    Espera = min(base_delay * factor**(n-1), max_delay) antes del intento n+1.
    No duerme después del último intento; si se agotan, relanza la última excepción.
    Las excepciones fuera de retry_on se propagan de inmediato sin reintentar.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_on:
            if attempt == attempts:
                raise
            delay = min(base_delay * (factor ** (attempt - 1)), max_delay)
            sleep(delay)
