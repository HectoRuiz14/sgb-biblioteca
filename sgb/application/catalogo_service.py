"""Servicio de aplicación para la gestión del catálogo de libros."""
from typing import List, Optional

from sgb.domain.catalogo.entities import Libro
from sgb.domain.catalogo.ports import (
    AutorRepositoryPort,
    CategoriaRepositoryPort,
    LibroRepositoryPort,
)
from sgb.domain.exceptions import (
    InvalidEjemplaresError,
    LibroConPrestamosError,
    LibroNotFoundError,
)


class CatalogoService:
    def __init__(
        self,
        libro_repo: LibroRepositoryPort,
        autor_repo: AutorRepositoryPort,
        categoria_repo: CategoriaRepositoryPort,
    ):
        self.libro_repo = libro_repo
        self.autor_repo = autor_repo
        self.categoria_repo = categoria_repo

    def crear_libro(
        self,
        titulo: str,
        autor: str,
        categoria: str,
        editorial: Optional[str] = None,
        anio: Optional[int] = None,
        ejemplares_totales: int = 1,
    ) -> Libro:
        autor_obj = self.autor_repo.obtener_o_crear(autor)
        categoria_obj = self.categoria_repo.obtener_o_crear(categoria)
        libro = Libro(
            titulo=titulo.strip(),
            editorial=editorial,
            anio=anio,
            ejemplares_totales=ejemplares_totales,
            ejemplares_disponibles=ejemplares_totales,
            autor_id=autor_obj.id,
            categoria_id=categoria_obj.id,
            autor=autor_obj,
            categoria=categoria_obj,
        )
        return self.libro_repo.crear(libro)

    def listar_libros(
        self,
        q: Optional[str] = None,
        categoria: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Libro]:
        libros = self.libro_repo.listar_con_autor()
        if categoria:
            libros = [l for l in libros if l.categoria and l.categoria.nombre == categoria]
        if q:
            ql = q.lower()
            libros = [
                l for l in libros
                if ql in l.titulo.lower() or (l.autor and ql in l.autor.nombre.lower())
            ]
        libros.sort(key=lambda l: l.id if l.id is not None else 0)
        return libros[skip:skip + limit]

    def obtener_libro(self, libro_id: int) -> Libro:
        libro = self.libro_repo.obtener(libro_id)
        if libro is None:
            raise LibroNotFoundError(f"Book with id {libro_id} not found")
        return libro

    def actualizar_libro(
        self,
        libro_id: int,
        titulo: str,
        autor: str,
        categoria: str,
        editorial: Optional[str] = None,
        anio: Optional[int] = None,
        ejemplares_totales: int = 1,
    ) -> Libro:
        libro = self.obtener_libro(libro_id)
        disponibles = libro.ejemplares_disponibles + (ejemplares_totales - libro.ejemplares_totales)
        if disponibles < 0:
            raise InvalidEjemplaresError("Total copies cannot be lower than the copies currently on loan")
        autor_obj = self.autor_repo.obtener_o_crear(autor)
        categoria_obj = self.categoria_repo.obtener_o_crear(categoria)
        actualizado = self.libro_repo.actualizar(
            libro_id,
            titulo=titulo.strip(),
            editorial=editorial,
            anio=anio,
            ejemplares_totales=ejemplares_totales,
            ejemplares_disponibles=disponibles,
            autor_id=autor_obj.id,
            categoria_id=categoria_obj.id,
        )
        if actualizado is None:
            raise LibroNotFoundError(f"Book with id {libro_id} not found")
        return actualizado

    def eliminar_libro(self, libro_id: int) -> bool:
        libro = self.obtener_libro(libro_id)
        if libro.prestamos or (hasattr(libro, "_orm_model") and libro._orm_model and libro._orm_model.prestamos):
            raise LibroConPrestamosError("Book has loan history and cannot be deleted")
        return self.libro_repo.eliminar(libro_id)
