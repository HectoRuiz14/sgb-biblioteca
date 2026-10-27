from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from sgb.api.deps import get_catalogo_service, get_current_user
from sgb.api.schemas import ErrorOut, LibroIn, LibroOut
from sgb.application.catalogo_service import CatalogoService
from sgb.domain.catalogo.entities import Libro
from sgb.domain.exceptions import (
    InvalidEjemplaresError,
    LibroConPrestamosError,
    LibroNotFoundError,
)

router = APIRouter(prefix="/api/v1/libros", tags=["Books"], dependencies=[Depends(get_current_user)])
R401 = {401: {"model": ErrorOut, "description": "Missing or invalid token"}}
R404 = {404: {"model": ErrorOut, "description": "Book not found"}, **R401}


def to_out(l: Libro) -> LibroOut:
    return LibroOut(
        id=l.id,
        titulo=l.titulo,
        autor=l.autor.nombre if l.autor else "",
        categoria=l.categoria.nombre if l.categoria else "",
        editorial=l.editorial,
        anio=l.anio,
        ejemplares_totales=l.ejemplares_totales,
        ejemplares_disponibles=l.ejemplares_disponibles,
    )


@router.post(
    "",
    response_model=LibroOut,
    status_code=status.HTTP_201_CREATED,
    responses=R401,
    summary="Create a book",
    description="Adds a book to the catalog. The author and category are created automatically if they do not exist.",
)
def crear_libro(
    data: LibroIn,
    service: CatalogoService = Depends(get_catalogo_service),
):
    libro = service.crear_libro(
        titulo=data.titulo,
        autor=data.autor,
        categoria=data.categoria,
        editorial=data.editorial,
        anio=data.anio,
        ejemplares_totales=data.ejemplares_totales,
    )
    return to_out(libro)


@router.get(
    "",
    response_model=list[LibroOut],
    responses=R401,
    summary="List books",
    description="Returns the catalog with author and category (single JOIN query). Supports text search, category filter and pagination.",
)
def listar_libros(
    q: str | None = Query(None, description="Search in title or author", examples=["quijote"]),
    categoria: str | None = Query(None, description="Exact category name", examples=["Novela"]),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    service: CatalogoService = Depends(get_catalogo_service),
):
    libros = service.listar_libros(q=q, categoria=categoria, skip=skip, limit=limit)
    return [to_out(l) for l in libros]


@router.get(
    "/{libro_id}",
    response_model=LibroOut,
    responses=R404,
    summary="Get a book by id",
    description="Returns one book, or 404 if it does not exist.",
)
def obtener_libro(
    libro_id: int,
    service: CatalogoService = Depends(get_catalogo_service),
):
    try:
        return to_out(service.obtener_libro(libro_id))
    except LibroNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Book with id {libro_id} not found")


@router.put(
    "/{libro_id}",
    response_model=LibroOut,
    responses={409: {"model": ErrorOut, "description": "Total copies lower than copies on loan"}, **R404},
    summary="Update a book",
    description="Replaces the book data. Changing the total copies adjusts the available copies by the same difference.",
)
def actualizar_libro(
    libro_id: int,
    data: LibroIn,
    service: CatalogoService = Depends(get_catalogo_service),
):
    try:
        libro = service.actualizar_libro(
            libro_id=libro_id,
            titulo=data.titulo,
            autor=data.autor,
            categoria=data.categoria,
            editorial=data.editorial,
            anio=data.anio,
            ejemplares_totales=data.ejemplares_totales,
        )
        return to_out(libro)
    except LibroNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Book with id {libro_id} not found")
    except InvalidEjemplaresError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Total copies cannot be lower than the copies currently on loan")


@router.delete(
    "/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={409: {"model": ErrorOut, "description": "Book has loan history"}, **R404},
    summary="Delete a book",
    description="Removes a book. Books with loan history cannot be deleted (409).",
)
def eliminar_libro(
    libro_id: int,
    service: CatalogoService = Depends(get_catalogo_service),
):
    try:
        service.eliminar_libro(libro_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except LibroNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Book with id {libro_id} not found")
    except LibroConPrestamosError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Book has loan history and cannot be deleted")
