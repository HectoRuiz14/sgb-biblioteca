"""Puertos abstractos para fuentes de datos abiertos y análisis."""
from abc import ABC, abstractmethod
from typing import List

from sgb.domain.datos_abiertos.entities import (
    BibliotecaPublica,
    CruceDivipolaResultado,
    EstadisticasBibliotecas,
    MunicipioDivipola,
)


class BibliotecasPort(ABC):
    """Puerto para consultar el catálogo de bibliotecas públicas."""

    @abstractmethod
    def obtener_bibliotecas(self, limite: int = 50) -> List[BibliotecaPublica]:
        """Obtiene una lista de bibliotecas públicas desde la fuente externa."""
        pass


class DivipolaPort(ABC):
    """Puerto para consultar la división político-administrativa (DIVIPOLA) de Colombia."""

    @abstractmethod
    def obtener_municipios(self, limite: int = 50) -> List[MunicipioDivipola]:
        """Obtiene la lista de municipios codificados por DANE DIVIPOLA."""
        pass


class AnalisisPort(ABC):
    """Puerto para procesamiento analítico de datos de bibliotecas y DIVIPOLA."""

    @abstractmethod
    def analizar_bibliotecas(self, bibliotecas: List[BibliotecaPublica]) -> EstadisticasBibliotecas:
        """Calcula estadísticas descriptivas y ranking de bibliotecas por municipio."""
        pass

    @abstractmethod
    def cruzar_con_divipola(
        self, bibliotecas: List[BibliotecaPublica], municipios: List[MunicipioDivipola]
    ) -> CruceDivipolaResultado:
        """Cruza bibliotecas con municipios de DIVIPOLA mediante normalización de nombres."""
        pass
