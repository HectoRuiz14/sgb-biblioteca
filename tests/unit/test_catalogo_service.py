"""Pruebas unitarias para CatalogoService usando unittest.mock (sin base de datos real)."""
from unittest.mock import MagicMock
import pytest

from sgb.application.catalogo_service import CatalogoService
from sgb.domain.catalogo.entities import Autor, Categoria, Libro
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


@pytest.fixture
def mock_repos():
    libro_repo = MagicMock(spec=LibroRepositoryPort)
    autor_repo = MagicMock(spec=AutorRepositoryPort)
    categoria_repo = MagicMock(spec=CategoriaRepositoryPort)
    return libro_repo, autor_repo, categoria_repo


def test_crear_libro_obtiene_o_crea_autor_y_categoria(mock_repos):
    libro_repo, autor_repo, categoria_repo = mock_repos
    service = CatalogoService(libro_repo, autor_repo, categoria_repo)

    autor_mock = Autor(id=10, nombre="Gabriel García Márquez")
    categoria_mock = Categoria(id=20, nombre="Realismo Mágico")
    autor_repo.obtener_o_crear.return_value = autor_mock
    categoria_repo.obtener_o_crear.return_value = categoria_mock

    libro_creado = Libro(
        id=1,
        titulo="Cien años de soledad",
        editorial="Sudamericana",
        anio=1967,
        ejemplares_totales=5,
        ejemplares_disponibles=5,
        autor_id=10,
        categoria_id=20,
        autor=autor_mock,
        categoria=categoria_mock,
    )
    libro_repo.crear.return_value = libro_creado

    resultado = service.crear_libro(
        titulo="Cien años de soledad",
        autor="Gabriel García Márquez",
        categoria="Realismo Mágico",
        editorial="Sudamericana",
        anio=1967,
        ejemplares_totales=5,
    )

    autor_repo.obtener_o_crear.assert_called_once_with("Gabriel García Márquez")
    categoria_repo.obtener_o_crear.assert_called_once_with("Realismo Mágico")
    libro_repo.crear.assert_called_once()
    assert resultado.id == 1
    assert resultado.titulo == "Cien años de soledad"


def test_actualizar_libro_falla_si_ejemplares_menor_que_prestados(mock_repos):
    libro_repo, autor_repo, categoria_repo = mock_repos
    service = CatalogoService(libro_repo, autor_repo, categoria_repo)

    # Libro con 5 totales y 2 disponibles (3 prestados)
    libro_existente = Libro(
        id=1,
        titulo="Libro Test",
        ejemplares_totales=5,
        ejemplares_disponibles=2,
    )
    libro_repo.obtener.return_value = libro_existente

    # Intentar reducir a 2 ejemplares totales (cuando hay 3 prestados: disponibles pasaría a 2 + (2-5) = -1)
    with pytest.raises(InvalidEjemplaresError):
        service.actualizar_libro(
            libro_id=1,
            titulo="Libro Test",
            autor="Autor Test",
            categoria="Cat Test",
            ejemplares_totales=2,
        )


def test_eliminar_libro_con_prestamos_lanza_error(mock_repos):
    libro_repo, autor_repo, categoria_repo = mock_repos
    service = CatalogoService(libro_repo, autor_repo, categoria_repo)

    prestamo_mock = MagicMock()
    libro_con_prestamos = Libro(
        id=1,
        titulo="Libro Prestado",
        prestamos=[prestamo_mock],
    )
    libro_repo.obtener.return_value = libro_con_prestamos

    with pytest.raises(LibroConPrestamosError):
        service.eliminar_libro(1)

    libro_repo.eliminar.assert_not_called()


def test_obtener_libro_inexistente_lanza_error(mock_repos):
    libro_repo, autor_repo, categoria_repo = mock_repos
    service = CatalogoService(libro_repo, autor_repo, categoria_repo)
    libro_repo.obtener.return_value = None

    with pytest.raises(LibroNotFoundError):
        service.obtener_libro(999)
