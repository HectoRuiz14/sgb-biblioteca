"""Servicio de aplicación para consultar fuentes de datos abiertos."""
from typing import List

from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola
from sgb.domain.datos_abiertos.ports import BibliotecasPort, DivipolaPort


class DatosAbiertosService:
    """Servicio de aplicación que orquesta los puertos de datos abiertos."""

    def __init__(
        self,
        bibliotecas_port: BibliotecasPort,
        divipola_port: DivipolaPort,
    ) -> None:
        self._bibliotecas_port = bibliotecas_port
        self._divipola_port = divipola_port

    def obtener_bibliotecas(self, limite: int = 50) -> List[BibliotecaPublica]:
        """Obtiene bibliotecas públicas mediante el puerto configurado."""
        return self._bibliotecas_port.obtener_bibliotecas(limite=limite)

    def obtener_municipios(self, limite: int = 50) -> List[MunicipioDivipola]:
        """Obtiene municipios de DIVIPOLA mediante el puerto configurado."""
        return self._divipola_port.obtener_municipios(limite=limite)
