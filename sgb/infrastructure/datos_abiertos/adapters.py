"""Adaptadores de infraestructura para APIs públicas colombianas con resiliencia."""
import time
from typing import Any, Callable, List, Optional

import httpx

from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import CircuitoAbiertoError, FuenteExternaError
from sgb.infrastructure.resilience import CircuitBreaker, retry_con_backoff


class _RetryableStatusError(Exception):
    """Error interno para respuestas HTTP 5xx o 429 reintentables."""
    pass


RETRYABLE_EXCEPTIONS = (
    httpx.RequestError,
    _RetryableStatusError,
    ConnectionError,
    TimeoutError,
)


class BibliotecasDatosGovAdapter(BibliotecasPort):
    """Adaptador para el dataset de bibliotecas de datos.gov.co con CircuitBreaker y Retry."""

    DEFAULT_URL = "https://www.datos.gov.co/resource/pkhg-bvje.json"

    def __init__(
        self,
        client: Optional[Any] = None,
        breaker: Optional[CircuitBreaker] = None,
        base_url: str = DEFAULT_URL,
        timeout: float = 10.0,
        retry_attempts: int = 3,
        base_delay: float = 0.5,
        factor: float = 2.0,
        max_delay: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._base_url = base_url
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._base_delay = base_delay
        self._factor = factor
        self._max_delay = max_delay
        self._sleep = sleep
        self._clock = clock
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exceptions=RETRYABLE_EXCEPTIONS,
            clock=clock,
        )

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def obtener_bibliotecas(self, limite: int = 50) -> List[BibliotecaPublica]:
        def _llamada_http() -> List[BibliotecaPublica]:
            params = {"$limit": str(limite)}
            try:
                resp = self._client.get(self._base_url, params=params, timeout=self._timeout)
            except (httpx.RequestError, ConnectionError, TimeoutError) as e:
                raise e

            if resp.status_code == 429 or resp.status_code >= 500:
                raise _RetryableStatusError(f"HTTP {resp.status_code}: {resp.text}")

            if 400 <= resp.status_code < 500:
                raise FuenteExternaError(f"Error cliente HTTP {resp.status_code}: {resp.text}")

            try:
                data = resp.json()
            except Exception as e:
                raise FuenteExternaError(f"JSON inválido devuelto por la fuente: {e}") from e

            if not isinstance(data, list):
                raise FuenteExternaError("Respuesta de la fuente no es una lista")

            resultado: List[BibliotecaPublica] = []
            for item in data:
                if not isinstance(item, dict):
                    raise FuenteExternaError("Elemento inválido en el JSON de la fuente")
                nombre = item.get("nombre_de_la_biblioteca")
                municipio = item.get("municipio")
                if not nombre or not municipio:
                    continue
                resultado.append(
                    BibliotecaPublica(
                        nombre=str(nombre).strip(),
                        municipio=str(municipio).strip(),
                        correo=item.get("correo_electronico"),
                        telefono=item.get("celular_de_contacto_del"),
                    )
                )
            return resultado

        def _operacion_con_retry() -> List[BibliotecaPublica]:
            return retry_con_backoff(
                _llamada_http,
                attempts=self._retry_attempts,
                base_delay=self._base_delay,
                factor=self._factor,
                max_delay=self._max_delay,
                retry_on=RETRYABLE_EXCEPTIONS,
                sleep=self._sleep,
            )

        try:
            return self._breaker.call(_operacion_con_retry)
        except RETRYABLE_EXCEPTIONS as e:
            raise FuenteExternaError(f"Error al consultar fuente de bibliotecas: {e}") from e


class DaneDivipolaAdapter(DivipolaPort):
    """Adaptador para el dataset DIVIPOLA (DANE) de datos.gov.co con CircuitBreaker y Retry."""

    DEFAULT_URL = "https://www.datos.gov.co/resource/gdxc-w37w.json"

    def __init__(
        self,
        client: Optional[Any] = None,
        breaker: Optional[CircuitBreaker] = None,
        base_url: str = DEFAULT_URL,
        timeout: float = 10.0,
        retry_attempts: int = 3,
        base_delay: float = 0.5,
        factor: float = 2.0,
        max_delay: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._base_url = base_url
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._base_delay = base_delay
        self._factor = factor
        self._max_delay = max_delay
        self._sleep = sleep
        self._clock = clock
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exceptions=RETRYABLE_EXCEPTIONS,
            clock=clock,
        )

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def obtener_municipios(self, limite: int = 50) -> List[MunicipioDivipola]:
        def _llamada_http() -> List[MunicipioDivipola]:
            params = {"$limit": str(limite)}
            try:
                resp = self._client.get(self._base_url, params=params, timeout=self._timeout)
            except (httpx.RequestError, ConnectionError, TimeoutError) as e:
                raise e

            if resp.status_code == 429 or resp.status_code >= 500:
                raise _RetryableStatusError(f"HTTP {resp.status_code}: {resp.text}")

            if 400 <= resp.status_code < 500:
                raise FuenteExternaError(f"Error cliente HTTP {resp.status_code}: {resp.text}")

            try:
                data = resp.json()
            except Exception as e:
                raise FuenteExternaError(f"JSON inválido devuelto por la fuente: {e}") from e

            if not isinstance(data, list):
                raise FuenteExternaError("Respuesta de la fuente no es una lista")

            resultado: List[MunicipioDivipola] = []
            for item in data:
                if not isinstance(item, dict):
                    raise FuenteExternaError("Elemento inválido en el JSON de la fuente")
                cod_mpio = item.get("cod_mpio")
                nom_mpio = item.get("nom_mpio")
                cod_dpto = item.get("cod_dpto")
                dpto = item.get("dpto")
                if not cod_mpio or not nom_mpio:
                    continue
                resultado.append(
                    MunicipioDivipola(
                        codigo_departamento=str(cod_dpto or "").strip(),
                        departamento=str(dpto or "").strip(),
                        codigo_municipio=str(cod_mpio).strip(),
                        municipio=str(nom_mpio).strip(),
                        tipo=str(item.get("tipo_municipio", "Municipio")).strip(),
                        longitud=item.get("longitud"),
                        latitud=item.get("latitud"),
                    )
                )
            return resultado

        def _operacion_con_retry() -> List[MunicipioDivipola]:
            return retry_con_backoff(
                _llamada_http,
                attempts=self._retry_attempts,
                base_delay=self._base_delay,
                factor=self._factor,
                max_delay=self._max_delay,
                retry_on=RETRYABLE_EXCEPTIONS,
                sleep=self._sleep,
            )

        try:
            return self._breaker.call(_operacion_con_retry)
        except RETRYABLE_EXCEPTIONS as e:
            raise FuenteExternaError(f"Error al consultar fuente DIVIPOLA: {e}") from e
