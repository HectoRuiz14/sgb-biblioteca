"""Servicio de aplicación para autenticación y usuarios."""
from typing import Optional, Tuple

from sgb.domain.exceptions import (
    EmailAlreadyRegisteredError,
    IdentificacionAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from sgb.domain.usuarios.entities import Usuario
from sgb.domain.usuarios.ports import (
    PasswordHasherPort,
    TokenPort,
    UsuarioRepositoryPort,
)


class UsuariosService:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
        token_service: TokenPort,
    ):
        self.usuario_repo = usuario_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    def register(
        self,
        nombre: str,
        identificacion: str,
        email: str,
        password: str,
        tipo_usuario: str = "estudiante",
        contacto: Optional[str] = None,
    ) -> Usuario:
        clean_email = email.strip().lower()
        clean_id = identificacion.strip()
        if self.usuario_repo.obtener_por_email(clean_email):
            raise EmailAlreadyRegisteredError("Email already registered")
        if self.usuario_repo.obtener_por_identificacion(clean_id):
            raise IdentificacionAlreadyRegisteredError("National ID already registered")

        pwd_hash = self.password_hasher.hash(password)
        usuario = Usuario(
            nombre=nombre,
            identificacion=clean_id,
            email=clean_email,
            tipo_usuario=tipo_usuario,
            contacto=contacto,
            password_hash=pwd_hash,
        )
        return self.usuario_repo.crear(usuario)

    def login(self, email: str, password: str) -> Tuple[str, Usuario]:
        clean_email = email.strip().lower()
        usuario = self.usuario_repo.obtener_por_email(clean_email)
        if usuario is None or not self.password_hasher.verify(password, usuario.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if not usuario.activo:
            raise InactiveUserError("Account is inactive")

        token = self.token_service.create_token(usuario.id)
        return token, usuario

    def obtener_por_id(self, usuario_id: int) -> Optional[Usuario]:
        return self.usuario_repo.obtener(usuario_id)
