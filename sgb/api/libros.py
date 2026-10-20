from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sgb.api.deps import get_current_user
from sgb.database import get_session
from sgb.models import Autor, Categoria, Libro
from sgb.repositories import LibroRepository
from sgb.schemas import ErrorOut, LibroIn, LibroOut

router = APIRouter(prefix="/api/v1/libros", tags=["Books"], dependencies=[Depends(get_current_user)])
R401 = {401: {"model": ErrorOut, "description": "Missing or invalid token"}}
R404 = {404: {"model": ErrorOut, "description": "Book not found"}, **R401}


def to_out(l: Libro) -> LibroOut:
    return LibroOut(id=l.id, titulo=l.titulo, autor=l.autor.nombre, categoria=l.categoria.nombre,
                    editorial=l.editorial, anio=l.anio, ejemplares_totales=l.ejemplares_totales,
                    ejemplares_disponibles=l.ejemplares_disponibles)


def _autor(session: Session, nombre: str) -> Autor:
    nombre = nombre.strip()
    obj = session.scalar(select(Autor).where(Autor.nombre == nombre))
    if obj is None:
        obj = Autor(nombre=nombre)
        session.add(obj)
        session.flush()
    return obj


def _categoria(session: Session, nombre: str) -> Categoria:
    nombre = nombre.strip()
    obj = session.scalar(select(Categoria).where(Categoria.nombre == nombre))
    if obj is None:
        obj = Categoria(nombre=nombre)
        session.add(obj)
        session.flush()
    return obj


def _get_or_404(repo: LibroRepository, libro_id: int) -> Libro:
    libro = repo.obtener(libro_id)
    if libro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Book with id {libro_id} not found")
    return libro


@router.post("", response_model=LibroOut, status_code=status.HTTP_201_CREATED, responses=R401,
             summary="Create a book",
             description="Adds a book to the catalog. The author and category are created automatically if they do not exist.")
def crear_libro(data: LibroIn, session: Session = Depends(get_session)):
    libro = Libro(titulo=data.titulo.strip(), editorial=data.editorial, anio=data.anio,
                  ejemplares_totales=data.ejemplares_totales, ejemplares_disponibles=data.ejemplares_totales,
                  autor_id=_autor(session, data.autor).id, categoria_id=_categoria(session, data.categoria).id)
    return to_out(LibroRepository(session).crear(libro))


@router.get("", response_model=list[LibroOut], responses=R401, summary="List books",
            description="Returns the catalog with author and category (single JOIN query). Supports text search, category filter and pagination.")
def listar_libros(q: str | None = Query(None, description="Search in title or author", examples=["quijote"]),
                  categoria: str | None = Query(None, description="Exact category name", examples=["Novela"]),
                  skip: int = Query(0, ge=0, description="Records to skip"),
                  limit: int = Query(50, ge=1, le=200, description="Max records to return"),
                  session: Session = Depends(get_session)):
    libros = LibroRepository(session).listar_con_autor()
    if categoria:
        libros = [l for l in libros if l.categoria.nombre == categoria]
    if q:
        ql = q.lower()
        libros = [l for l in libros if ql in l.titulo.lower() or ql in l.autor.nombre.lower()]
    libros.sort(key=lambda l: l.id)
    return [to_out(l) for l in libros[skip:skip + limit]]


@router.get("/{libro_id}", response_model=LibroOut, responses=R404, summary="Get a book by id",
            description="Returns one book, or 404 if it does not exist.")
def obtener_libro(libro_id: int, session: Session = Depends(get_session)):
    return to_out(_get_or_404(LibroRepository(session), libro_id))


@router.put("/{libro_id}", response_model=LibroOut,
            responses={409: {"model": ErrorOut, "description": "Total copies lower than copies on loan"}, **R404},
            summary="Update a book",
            description="Replaces the book data. Changing the total copies adjusts the available copies by the same difference.")
def actualizar_libro(libro_id: int, data: LibroIn, session: Session = Depends(get_session)):
    repo = LibroRepository(session)
    libro = _get_or_404(repo, libro_id)
    disponibles = libro.ejemplares_disponibles + (data.ejemplares_totales - libro.ejemplares_totales)
    if disponibles < 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Total copies cannot be lower than the copies currently on loan")
    repo.actualizar(libro_id, titulo=data.titulo.strip(), editorial=data.editorial, anio=data.anio,
                    ejemplares_totales=data.ejemplares_totales, ejemplares_disponibles=disponibles,
                    autor_id=_autor(session, data.autor).id, categoria_id=_categoria(session, data.categoria).id)
    session.refresh(libro)
    return to_out(libro)


@router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={409: {"model": ErrorOut, "description": "Book has loan history"}, **R404},
               summary="Delete a book", description="Removes a book. Books with loan history cannot be deleted (409).")
def eliminar_libro(libro_id: int, session: Session = Depends(get_session)):
    repo = LibroRepository(session)
    libro = _get_or_404(repo, libro_id)
    if libro.prestamos:
        raise HTTPException(status.HTTP_409_CONFLICT, "Book has loan history and cannot be deleted")
    repo.eliminar(libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
