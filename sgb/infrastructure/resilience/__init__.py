"""Componentes de resiliencia para llamadas externas."""
from .circuit_breaker import CircuitBreaker, CircuitState
from .retry import retry_con_backoff

__all__ = ["CircuitBreaker", "CircuitState", "retry_con_backoff"]
