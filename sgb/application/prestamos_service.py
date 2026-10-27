"""Servicio de aplicación para la gestión de préstamos."""
from typing import List, Optional

from sgb.domain.exceptions import PrestamoNotFoundError
from sgb.domain.prestamos.entities import Prestamo
from sgb.domain.prestamos.ports import PrestamoRepositoryPort


class PrestamosService:
    def __init__(self, prestamo_repo: PrestamoRepositoryPort):
        self.prestamo_repo = prestamo_repo

    def crear_prestamo(self, libro_id: int, usuario_id: int) -> Prestamo:
        return self.prestamo_repo.crear(libro_id=libro_id, usuario_id=usuario_id)

    def obtener_prestamo(self, prestamo_id: int) -> Prestamo:
        prestamo = self.prestamo_repo.obtener(prestamo_id)
        if prestamo is None:
            raise PrestamoNotFoundError(f"Prestamo with id {prestamo_id} not found")
        return prestamo

    def listar_prestamos(self) -> List[Prestamo]:
        return self.prestamo_repo.listar()

    def registrar_devolucion(self, prestamo_id: int) -> Prestamo:
        prestamo = self.prestamo_repo.registrar_devolucion(prestamo_id)
        if prestamo is None:
            raise PrestamoNotFoundError(f"Prestamo with id {prestamo_id} not found")
        return prestamo

    def eliminar_prestamo(self, prestamo_id: int) -> bool:
        return self.prestamo_repo.eliminar(prestamo_id)

    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        return self.prestamo_repo.historial_por_usuario(usuario_id)
