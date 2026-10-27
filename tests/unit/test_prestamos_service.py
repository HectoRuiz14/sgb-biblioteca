"""Pruebas unitarias para PrestamosService usando unittest.mock (sin base de datos real)."""
from datetime import date, timedelta
from unittest.mock import MagicMock
import pytest

from sgb.application.prestamos_service import PrestamosService
from sgb.domain.catalogo.entities import Libro
from sgb.domain.catalogo.ports import LibroRepositoryPort
from sgb.domain.exceptions import (
    LibroNotFoundError,
    PrestamoNotFoundError,
    PrestamoYaDevueltoError,
    SinEjemplaresError,
    UsuarioNotFoundError,
)
from sgb.domain.prestamos.entities import Prestamo
from sgb.domain.prestamos.ports import PrestamoRepositoryPort, UnitOfWorkPort
from sgb.domain.usuarios.entities import Usuario
from sgb.domain.usuarios.ports import UsuarioRepositoryPort


@pytest.fixture
def mock_deps():
    prestamo_repo = MagicMock(spec=PrestamoRepositoryPort)
    libro_repo = MagicMock(spec=LibroRepositoryPort)
    usuario_repo = MagicMock(spec=UsuarioRepositoryPort)
    uow = MagicMock(spec=UnitOfWorkPort)
    return prestamo_repo, libro_repo, usuario_repo, uow


def test_prestamo_exitoso_docente_15_dias_y_stock_descontado(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    hoy_fijo = date(2026, 10, 27)
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow, hoy=lambda: hoy_fijo)

    usuario = Usuario(id=1, nombre="Profesor", identificacion="D001", tipo_usuario="docente")
    libro = Libro(id=10, titulo="Clean Architecture", ejemplares_totales=3, ejemplares_disponibles=3)

    usuario_repo.obtener.return_value = usuario
    libro_repo.obtener.return_value = libro
    prestamo_repo.agregar.side_effect = lambda p, commit=True: p

    prestamo = service.crear_prestamo(libro_id=10, usuario_id=1)

    assert prestamo.fecha_prestamo == hoy_fijo
    assert prestamo.fecha_limite == hoy_fijo + timedelta(days=15)
    libro_repo.actualizar.assert_called_once_with(10, commit=False, ejemplares_disponibles=2)
    prestamo_repo.agregar.assert_called_once()
    uow.commit.assert_called_once()
    uow.rollback.assert_not_called()


def test_crear_prestamo_sin_ejemplares_lanza_error_y_no_guarda(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    usuario = Usuario(id=1, nombre="Alumno", identificacion="A001", tipo_usuario="estudiante")
    libro = Libro(id=10, titulo="Libro Agotado", ejemplares_totales=2, ejemplares_disponibles=0)

    usuario_repo.obtener.return_value = usuario
    libro_repo.obtener.return_value = libro

    with pytest.raises(SinEjemplaresError):
        service.crear_prestamo(libro_id=10, usuario_id=1)

    libro_repo.actualizar.assert_not_called()
    prestamo_repo.agregar.assert_not_called()
    uow.commit.assert_not_called()
    uow.rollback.assert_not_called()


def test_crear_prestamo_libro_inexistente_lanza_error(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    usuario = Usuario(id=1, nombre="Alumno", identificacion="A001")
    usuario_repo.obtener.return_value = usuario
    libro_repo.obtener.return_value = None

    with pytest.raises(LibroNotFoundError):
        service.crear_prestamo(libro_id=999, usuario_id=1)

    libro_repo.actualizar.assert_not_called()
    prestamo_repo.agregar.assert_not_called()
    uow.commit.assert_not_called()
    uow.rollback.assert_not_called()


def test_crear_prestamo_usuario_inexistente_lanza_error(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    usuario_repo.obtener.return_value = None

    with pytest.raises(UsuarioNotFoundError):
        service.crear_prestamo(libro_id=10, usuario_id=999)

    libro_repo.actualizar.assert_not_called()
    prestamo_repo.agregar.assert_not_called()
    uow.commit.assert_not_called()
    uow.rollback.assert_not_called()


def test_devolucion_a_tiempo_multa_cero_y_stock_repuesto(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    hoy_fijo = date(2026, 10, 27)
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow, hoy=lambda: hoy_fijo)

    prestamo = Prestamo(
        id=5,
        libro_id=10,
        usuario_id=1,
        fecha_prestamo=hoy_fijo - timedelta(days=5),
        fecha_limite=hoy_fijo + timedelta(days=3),
        fecha_devolucion=None,
    )
    libro = Libro(id=10, titulo="Libro", ejemplares_totales=3, ejemplares_disponibles=1)

    prestamo_repo.obtener.return_value = prestamo
    libro_repo.obtener.return_value = libro
    prestamo_repo.guardar.side_effect = lambda p, commit=True: p

    devuelto = service.registrar_devolucion(5)

    assert devuelto.fecha_devolucion == hoy_fijo
    assert devuelto.multa == 0.0
    libro_repo.actualizar.assert_called_once_with(10, commit=False, ejemplares_disponibles=2)
    prestamo_repo.guardar.assert_called_once()
    uow.commit.assert_called_once()
    uow.rollback.assert_not_called()


def test_devolucion_tardia_calcula_multa_y_repone_stock(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    hoy_fijo = date(2026, 10, 27)
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow, hoy=lambda: hoy_fijo)

    # 4 días de retraso -> multa = 4 * 1000 = 4000
    prestamo = Prestamo(
        id=5,
        libro_id=10,
        usuario_id=1,
        fecha_prestamo=hoy_fijo - timedelta(days=12),
        fecha_limite=hoy_fijo - timedelta(days=4),
        fecha_devolucion=None,
    )
    libro = Libro(id=10, titulo="Libro", ejemplares_totales=3, ejemplares_disponibles=1)

    prestamo_repo.obtener.return_value = prestamo
    libro_repo.obtener.return_value = libro
    prestamo_repo.guardar.side_effect = lambda p, commit=True: p

    devuelto = service.registrar_devolucion(5)

    assert devuelto.fecha_devolucion == hoy_fijo
    assert devuelto.multa == 4000.0
    libro_repo.actualizar.assert_called_once_with(10, commit=False, ejemplares_disponibles=2)
    prestamo_repo.guardar.assert_called_once()
    uow.commit.assert_called_once()
    uow.rollback.assert_not_called()


def test_devolucion_repetida_lanza_error_sin_cambio(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    prestamo_ya_devuelto = Prestamo(
        id=5,
        libro_id=10,
        usuario_id=1,
        fecha_prestamo=date(2026, 10, 1),
        fecha_limite=date(2026, 10, 9),
        fecha_devolucion=date(2026, 10, 8),
    )
    prestamo_repo.obtener.return_value = prestamo_ya_devuelto

    with pytest.raises(PrestamoYaDevueltoError):
        service.registrar_devolucion(5)

    libro_repo.actualizar.assert_not_called()
    prestamo_repo.guardar.assert_not_called()
    uow.commit.assert_not_called()
    uow.rollback.assert_not_called()


def test_devolucion_prestamo_inexistente_lanza_error(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    prestamo_repo.obtener.return_value = None

    with pytest.raises(PrestamoNotFoundError):
        service.registrar_devolucion(999)

    libro_repo.actualizar.assert_not_called()
    prestamo_repo.guardar.assert_not_called()
    uow.commit.assert_not_called()
    uow.rollback.assert_not_called()


def test_commit_falla_llama_rollback_y_propaga_excepcion(mock_deps):
    prestamo_repo, libro_repo, usuario_repo, uow = mock_deps
    service = PrestamosService(prestamo_repo, libro_repo, usuario_repo, uow)

    usuario = Usuario(id=1, nombre="Alumno", identificacion="A001")
    libro = Libro(id=10, titulo="Libro", ejemplares_totales=2, ejemplares_disponibles=2)

    usuario_repo.obtener.return_value = usuario
    libro_repo.obtener.return_value = libro
    prestamo_repo.agregar.side_effect = lambda p, commit=True: p

    uow.commit.side_effect = RuntimeError("DB transaction failure")

    with pytest.raises(RuntimeError, match="DB transaction failure"):
        service.crear_prestamo(libro_id=10, usuario_id=1)

    uow.rollback.assert_called_once()
