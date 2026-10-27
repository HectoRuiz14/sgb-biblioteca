"""Puertos (interfaces abstractas) para el Bounded Context Catálogo."""
from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Libro


class LibroRepositoryPort(ABC):
    @abstractmethod
    def crear(self, libro: Libro) -> Libro:
        """Crea un nuevo libro en el catálogo."""
        pass

    @abstractmethod
    def obtener(self, libro_id: int) -> Optional[Libro]:
        """Obtiene un libro por su ID."""
        pass

    @abstractmethod
    def listar(self) -> List[Libro]:
        """Lista todos los libros."""
        pass

    @abstractmethod
    def actualizar(self, libro_id: int, **campos) -> Optional[Libro]:
        """Actualiza campos específicos de un libro."""
        pass

    @abstractmethod
    def eliminar(self, libro_id: int) -> bool:
        """Elimina un libro del catálogo."""
        pass

    @abstractmethod
    def listar_con_autor(self) -> List[Libro]:
        """Lista libros con autor y categoría cargados en una sola operación."""
        pass
