"""Puertos abstractos para fuentes de datos abiertos."""
from abc import ABC, abstractmethod
from typing import List

from sgb.domain.datos_abiertos.entities import BibliotecaPublica, MunicipioDivipola


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
