"""Servicio de aplicación para análisis analítico de datos abiertos con DuckDB."""
from sgb.domain.datos_abiertos.entities import (
    CruceDivipolaResultado,
    EstadisticasBibliotecas,
)
from sgb.domain.datos_abiertos.ports import (
    AnalisisPort,
    BibliotecasPort,
    DivipolaPort,
)


class AnalisisService:
    """Servicio que coordina la ingesta de datos abiertos y su procesamiento analítico."""

    def __init__(
        self,
        bibliotecas_port: BibliotecasPort,
        divipola_port: DivipolaPort,
        analisis_port: AnalisisPort,
    ) -> None:
        self._bibliotecas_port = bibliotecas_port
        self._divipola_port = divipola_port
        self._analisis_port = analisis_port

    def obtener_estadisticas_bibliotecas(self, limite: int = 200) -> EstadisticasBibliotecas:
        """Obtiene las bibliotecas desde el puerto y calcula sus estadísticas agregadas."""
        bibliotecas = self._bibliotecas_port.obtener_bibliotecas(limite=limite)
        return self._analisis_port.analizar_bibliotecas(bibliotecas)

    def obtener_cruce_divipola(
        self, limite_bibliotecas: int = 200, limite_divipola: int = 1200
    ) -> CruceDivipolaResultado:
        """Obtiene bibliotecas y municipios y ejecuta el cruce analítico."""
        bibliotecas = self._bibliotecas_port.obtener_bibliotecas(limite=limite_bibliotecas)
        municipios = self._divipola_port.obtener_municipios(limite=limite_divipola)
        return self._analisis_port.cruzar_con_divipola(bibliotecas, municipios)
