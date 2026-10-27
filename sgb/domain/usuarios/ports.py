"""Puertos (interfaces abstractas) para el Bounded Context Usuarios y Seguridad."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        """Obtiene un usuario por su correo electrónico."""
        pass

    @abstractmethod
    def obtener_por_identificacion(self, identificacion: str) -> Optional[Usuario]:
        """Obtiene un usuario por su documento de identificación."""
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


class PasswordHasherPort(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        """Genera un hash seguro para la contraseña."""
        pass

    @abstractmethod
    def verify(self, password: str, stored: Optional[str]) -> bool:
        """Verifica una contraseña contra un hash almacenado."""
        pass


class TokenPort(ABC):
    @abstractmethod
    def create_token(self, user_id: int, minutes: Optional[int] = None) -> str:
        """Genera un token de acceso para un usuario."""
        pass

    @abstractmethod
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decodifica y valida un token de acceso."""
        pass
