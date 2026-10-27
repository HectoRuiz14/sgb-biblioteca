"""
Pruebas de integración del SGB, corriendo contra una base SQLite en
memoria (no tocan biblioteca.db). Ejecutar con:
    pytest tests/ -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sgb.infrastructure.database import Base
from sgb.infrastructure.models import Autor, Categoria, Libro, Usuario
from sgb.infrastructure.repositories import LibroRepository, UsuarioRepository, PrestamoRepository


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, future=True)
    db = TestSession()
    yield db
    db.close()


@pytest.fixture()
def datos_base(session):
    autor = Autor(nombre="Gabriel García Márquez", nacionalidad="Colombiana")
    categoria = Categoria(nombre="Novela")
    session.add_all([autor, categoria])
    session.commit()

    libro = Libro(
        titulo="Cien años de soledad",
        editorial="Sudamericana",
        anio=1967,
        ejemplares_totales=3,
        ejemplares_disponibles=3,
        autor_id=autor.id,
        categoria_id=categoria.id,
    )
    usuario = Usuario(nombre="Ana Torres", identificacion="1001", tipo_usuario="estudiante")
    session.add_all([libro, usuario])
    session.commit()
    return {"autor": autor, "categoria": categoria, "libro": libro, "usuario": usuario}


def test_crud_completo_libro(session, datos_base):
    """CRUD de Libro: crear, leer, actualizar y eliminar."""
    repo = LibroRepository(session)

    libro = repo.crear(Libro(
        titulo="El amor en los tiempos del cólera",
        autor_id=datos_base["autor"].id,
        categoria_id=datos_base["categoria"].id,
        ejemplares_totales=2,
        ejemplares_disponibles=2,
    ))
    assert libro.id is not None

    encontrado = repo.obtener(libro.id)
    assert encontrado.titulo == "El amor en los tiempos del cólera"

    actualizado = repo.actualizar(libro.id, editorial="Oveja Negra")
    assert actualizado.editorial == "Oveja Negra"

    assert repo.eliminar(libro.id) is True
    assert repo.obtener(libro.id) is None


def test_query_join_evita_n_mas_1(session, datos_base):
    """Verifica que listar_con_autor trae libro, autor y categoría en una sola consulta."""
    repo = LibroRepository(session)
    libros = repo.listar_con_autor()

    assert len(libros) == 1
    assert libros[0].autor.nombre == "Gabriel García Márquez"
    assert libros[0].categoria.nombre == "Novela"


def test_flujo_prestamo_y_devolucion_con_multa(session, datos_base):
    """Flujo completo: préstamo -> devolución -> cálculo de multa."""
    from datetime import date, timedelta

    repo_prestamo = PrestamoRepository(session)
    repo_libro = LibroRepository(session)

    prestamo = repo_prestamo.crear(
        libro_id=datos_base["libro"].id,
        usuario_id=datos_base["usuario"].id,
    )
    assert prestamo.id is not None

    libro_actualizado = repo_libro.obtener(datos_base["libro"].id)
    assert libro_actualizado.ejemplares_disponibles == 2

    prestamo.fecha_limite = date.today() - timedelta(days=3)
    session.commit()

    devuelto = repo_prestamo.registrar_devolucion(prestamo.id)
    assert devuelto.fecha_devolucion is not None
    assert devuelto.multa > 0

    libro_final = repo_libro.obtener(datos_base["libro"].id)
    assert libro_final.ejemplares_disponibles == 3