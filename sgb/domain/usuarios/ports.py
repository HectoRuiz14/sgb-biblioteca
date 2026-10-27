"""Puertos (interfaces abstractas) para el Bounded Context Usuarios."""
from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Usuario


class UsuarioRepositoryPort(ABC):
    @abstractmethod
    def crear(self, usuario: Usuario) -> Usuario:
        """Crea un nuevo usuario."""
        pass

    @abstractmethod
    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        """Obtiene un usuario por su ID."""
        pass

    @abstractmethod
    def listar(self) -> List[Usuario]:
        """Lista todos los usuarios."""
        pass

    @abstractmethod
    def actualizar(self, usuario_id: int, **campos) -> Optional[Usuario]:
        """Actualiza campos específicos de un usuario."""
        pass

    @abstractmethod
    def eliminar(self, usuario_id: int) -> bool:
        """Elimina un usuario."""
        pass
