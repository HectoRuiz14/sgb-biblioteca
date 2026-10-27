"""Servicio de aplicación para la gestión de préstamos."""
from datetime import date
from typing import Callable, List

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
from sgb.domain.usuarios.ports import UsuarioRepositoryPort


class PrestamosService:
    def __init__(
        self,
        prestamo_repo: PrestamoRepositoryPort,
        libro_repo: LibroRepositoryPort,
        usuario_repo: UsuarioRepositoryPort,
        uow: UnitOfWorkPort,
        hoy: Callable[[], date] = date.today,
    ):
        self.prestamo_repo = prestamo_repo
        self.libro_repo = libro_repo
        self.usuario_repo = usuario_repo
        self.uow = uow
        self.hoy = hoy

    def crear_prestamo(self, libro_id: int, usuario_id: int) -> Prestamo:
        # Validaciones previas al bloque transaccional
        usuario = self.usuario_repo.obtener(usuario_id)
        if usuario is None:
            raise UsuarioNotFoundError(f"User with id {usuario_id} not found")

        libro = self.libro_repo.obtener(libro_id)
        if libro is None:
            raise LibroNotFoundError(f"Book with id {libro_id} not found")

        if libro.ejemplares_disponibles < 1:
            raise SinEjemplaresError("No copies available for loan")

        fecha_actual = self.hoy()
        fecha_limite = Prestamo.calcular_fecha_limite(usuario.tipo_usuario, desde=fecha_actual)

        try:
            self.libro_repo.actualizar(
                libro.id,
                commit=False,
                ejemplares_disponibles=libro.ejemplares_disponibles - 1,
            )
            nuevo_prestamo = Prestamo(
                libro_id=libro.id,
                usuario_id=usuario.id,
                fecha_prestamo=fecha_actual,
                fecha_limite=fecha_limite,
            )
            prestamo_guardado = self.prestamo_repo.agregar(nuevo_prestamo, commit=False)
            self.uow.commit()
            return prestamo_guardado
        except Exception:
            self.uow.rollback()
            raise

    def registrar_devolucion(self, prestamo_id: int) -> Prestamo:
        # Validaciones previas al bloque transaccional
        prestamo = self.prestamo_repo.obtener(prestamo_id)
        if prestamo is None:
            raise PrestamoNotFoundError(f"Prestamo with id {prestamo_id} not found")

        if prestamo.fecha_devolucion is not None:
            raise PrestamoYaDevueltoError("Loan has already been returned")

        libro = self.libro_repo.obtener(prestamo.libro_id)
        if libro is None:
            raise LibroNotFoundError(f"Book with id {prestamo.libro_id} not found")

        fecha_actual = self.hoy()
        prestamo.fecha_devolucion = fecha_actual
        prestamo.calcular_multa(fecha_actual)

        try:
            self.libro_repo.actualizar(
                libro.id,
                commit=False,
                ejemplares_disponibles=libro.ejemplares_disponibles + 1,
            )
            prestamo_guardado = self.prestamo_repo.guardar(prestamo, commit=False)
            self.uow.commit()
            return prestamo_guardado
        except Exception:
            self.uow.rollback()
            raise

    def obtener_prestamo(self, prestamo_id: int) -> Prestamo:
        prestamo = self.prestamo_repo.obtener(prestamo_id)
        if prestamo is None:
            raise PrestamoNotFoundError(f"Prestamo with id {prestamo_id} not found")
        return prestamo

    def listar_prestamos(self) -> List[Prestamo]:
        return self.prestamo_repo.listar()

    def eliminar_prestamo(self, prestamo_id: int) -> bool:
        return self.prestamo_repo.eliminar(prestamo_id)

    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        return self.prestamo_repo.historial_por_usuario(usuario_id)
