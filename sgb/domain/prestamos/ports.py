"""Puertos (interfaces abstractas) para el Bounded Context Préstamos."""
from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Prestamo


class PrestamoRepositoryPort(ABC):
    @abstractmethod
    def agregar(self, prestamo: Prestamo, commit: bool = True) -> Prestamo:
        """Persiste una nueva entidad de préstamo."""
        pass

    @abstractmethod
    def guardar(self, prestamo: Prestamo, commit: bool = True) -> Prestamo:
        """Actualiza un préstamo existente."""
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
    def eliminar(self, prestamo_id: int) -> bool:
        """Elimina un registro de préstamo."""
        pass

    @abstractmethod
    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        """Obtiene el historial de préstamos de un usuario."""
        pass


class UnitOfWorkPort(ABC):
    @abstractmethod
    def commit(self) -> None:
        """Confirma la transacción activa."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Revierte la transacción activa."""
        pass
