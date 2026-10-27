"""Puertos (interfaces abstractas) para el Bounded Context Catálogo."""
from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Autor, Categoria, Libro


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
    def actualizar(self, libro_id: int, commit: bool = True, **campos) -> Optional[Libro]:
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


class AutorRepositoryPort(ABC):
    @abstractmethod
    def obtener_por_nombre(self, nombre: str) -> Optional[Autor]:
        pass

    @abstractmethod
    def crear(self, autor: Autor) -> Autor:
        pass

    @abstractmethod
    def obtener_o_crear(self, nombre: str) -> Autor:
        pass


class CategoriaRepositoryPort(ABC):
    @abstractmethod
    def obtener_por_nombre(self, nombre: str) -> Optional[Categoria]:
        pass

    @abstractmethod
    def crear(self, categoria: Categoria) -> Categoria:
        pass

    @abstractmethod
    def obtener_o_crear(self, nombre: str) -> Categoria:
        pass
