"""Puertos (interfaces abstractas) para el Bounded Context Préstamos."""
from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Prestamo


class PrestamoRepositoryPort(ABC):
    @abstractmethod
    def crear(self, libro_id: int, usuario_id: int) -> Prestamo:
        """Crea un nuevo préstamo verificando disponibilidad."""
        pass

    @abstractmethod
    def obtener(self, prestamo_id: int) -> Optional[Prestamo]:
        """Obtiene un préstamo por su ID."""
        pass

    @abstractmethod
    def listar(self) -> List[Prestamo]:
        """Lista todos los préstamos."""
        pass

    @abstractmethod
    def registrar_devolucion(self, prestamo_id: int) -> Optional[Prestamo]:
        """Registra la devolución, calcula multa y restaura stock."""
        pass

    @abstractmethod
    def eliminar(self, prestamo_id: int) -> bool:
        """Elimina un registro de préstamo."""
        pass

    @abstractmethod
    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        """Obtiene el historial de préstamos de un usuario."""
        pass
