"""Adaptadores de infraestructura para APIs públicas colombianas con resiliencia."""
import time
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Optional

import httpx

from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort
from sgb.domain.exceptions import FuenteExternaError
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


class _SocrataJsonAdapter:
    """Clase base privada con la lógica común de resiliencia y HTTP para adaptadores Socrata."""

    DEFAULT_URL: str = ""
    ERROR_LABEL: str = "fuente externa"

    def __init__(
        self,
        client: Optional[Any] = None,
        breaker: Optional[CircuitBreaker] = None,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        retry_attempts: int = 3,
        base_delay: float = 0.5,
        factor: float = 2.0,
        max_delay: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._base_url = base_url or self.DEFAULT_URL
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

    @abstractmethod
    def _mapear(self, registro: Dict[str, Any]) -> Any:
        """Mapea un dict JSON a la entidad de dominio. Devuelve None si debe ignorarse."""
        ...

    def _consultar(self, limite: int) -> List[Any]:
        """Ejecuta la consulta HTTP con breaker + retry, parsea JSON y mapea a entidades."""
        def _llamada_http() -> List[Any]:
            params = {"$limit": str(limite)}
            resp = self._client.get(self._base_url, params=params, timeout=self._timeout)

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

            resultado: List[Any] = []
            for item in data:
                if not isinstance(item, dict):
                    raise FuenteExternaError("Elemento inválido en el JSON de la fuente")
                entidad = self._mapear(item)
                if entidad is not None:
                    resultado.append(entidad)
            return resultado

        def _operacion_con_retry() -> List[Any]:
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
            raise FuenteExternaError(f"Error al consultar {self.ERROR_LABEL}: {e}") from e


class BibliotecasDatosGovAdapter(_SocrataJsonAdapter, BibliotecasPort):
    """Adaptador para el dataset de bibliotecas de datos.gov.co con CircuitBreaker y Retry."""

    DEFAULT_URL = "https://www.datos.gov.co/resource/pkhg-bvje.json"
    ERROR_LABEL = "fuente de bibliotecas"

    def _mapear(self, registro: Dict[str, Any]) -> Optional[BibliotecaPublica]:
        nombre = registro.get("nombre_de_la_biblioteca")
        municipio = registro.get("municipio")
        if not nombre or not municipio:
            return None
        return BibliotecaPublica(
            nombre=str(nombre).strip(),
            municipio=str(municipio).strip(),
            correo=registro.get("correo_electronico"),
            telefono=registro.get("celular_de_contacto_del"),
        )

    def obtener_bibliotecas(self, limite: int = 50) -> List[BibliotecaPublica]:
        return self._consultar(limite)


class DaneDivipolaAdapter(_SocrataJsonAdapter, DivipolaPort):
    """Adaptador para el dataset DIVIPOLA (DANE) de datos.gov.co con CircuitBreaker y Retry."""

    DEFAULT_URL = "https://www.datos.gov.co/resource/gdxc-w37w.json"
    ERROR_LABEL = "fuente DIVIPOLA"

    def _mapear(self, registro: Dict[str, Any]) -> Optional[MunicipioDivipola]:
        cod_mpio = registro.get("cod_mpio")
        nom_mpio = registro.get("nom_mpio")
        if not cod_mpio or not nom_mpio:
            return None
        return MunicipioDivipola(
            codigo_departamento=str(registro.get("cod_dpto") or "").strip(),
            departamento=str(registro.get("dpto") or "").strip(),
            codigo_municipio=str(cod_mpio).strip(),
            municipio=str(nom_mpio).strip(),
            tipo=str(registro.get("tipo_municipio", "Municipio")).strip(),
            longitud=registro.get("longitud"),
            latitud=registro.get("latitud"),
        )

    def obtener_municipios(self, limite: int = 50) -> List[MunicipioDivipola]:
        return self._consultar(limite)
