"""Pruebas unitarias para UsuariosService usando unittest.mock (sin base de datos real)."""
from unittest.mock import MagicMock
import pytest

from sgb.application.usuarios_service import UsuariosService
from sgb.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from sgb.domain.usuarios.entities import Usuario
from sgb.domain.usuarios.ports import (
    PasswordHasherPort,
    TokenPort,
    UsuarioRepositoryPort,
)


@pytest.fixture
def mock_usuarios_deps():
    usuario_repo = MagicMock(spec=UsuarioRepositoryPort)
    hasher = MagicMock(spec=PasswordHasherPort)
    token_service = MagicMock(spec=TokenPort)
    return usuario_repo, hasher, token_service


def test_register_usuario_exitoso(mock_usuarios_deps):
    usuario_repo, hasher, token_service = mock_usuarios_deps
    service = UsuariosService(usuario_repo, hasher, token_service)

    usuario_repo.obtener_por_email.return_value = None
    usuario_repo.obtener_por_identificacion.return_value = None
    hasher.hash.return_value = "hashed_pw_123"

    usuario_creado = Usuario(
        id=1,
        nombre="Carlos",
        identificacion="12345",
        email="carlos@example.com",
        tipo_usuario="estudiante",
        password_hash="hashed_pw_123",
    )
    usuario_repo.crear.return_value = usuario_creado

    resultado = service.register(
        nombre="Carlos",
        identificacion="12345",
        email="carlos@example.com",
        password="plain_password",
    )

    hasher.hash.assert_called_once_with("plain_password")
    usuario_repo.crear.assert_called_once()
    assert resultado.id == 1
    assert resultado.email == "carlos@example.com"


def test_register_email_duplicado_lanza_error(mock_usuarios_deps):
    usuario_repo, hasher, token_service = mock_usuarios_deps
    service = UsuariosService(usuario_repo, hasher, token_service)

    usuario_repo.obtener_por_email.return_value = Usuario(id=1, email="existente@example.com")

    with pytest.raises(EmailAlreadyRegisteredError):
        service.register(
            nombre="Otro",
            identificacion="999",
            email="existente@example.com",
            password="secreta",
        )


def test_login_exitoso(mock_usuarios_deps):
    usuario_repo, hasher, token_service = mock_usuarios_deps
    service = UsuariosService(usuario_repo, hasher, token_service)

    usuario_db = Usuario(
        id=7,
        nombre="Ana",
        identificacion="777",
        email="ana@example.com",
        activo=True,
        password_hash="hashed_clave",
    )
    usuario_repo.obtener_por_email.return_value = usuario_db
    hasher.verify.return_value = True
    token_service.create_token.return_value = "jwt.token.mock"

    token, usuario = service.login("ana@example.com", "clave_correcta")

    hasher.verify.assert_called_once_with("clave_correcta", "hashed_clave")
    token_service.create_token.assert_called_once_with(7)
    assert token == "jwt.token.mock"
    assert usuario.id == 7


def test_login_clave_invalida_lanza_error(mock_usuarios_deps):
    usuario_repo, hasher, token_service = mock_usuarios_deps
    service = UsuariosService(usuario_repo, hasher, token_service)

    usuario_db = Usuario(
        id=7,
        email="ana@example.com",
        activo=True,
        password_hash="hashed_clave",
    )
    usuario_repo.obtener_por_email.return_value = usuario_db
    hasher.verify.return_value = False

    with pytest.raises(InvalidCredentialsError):
        service.login("ana@example.com", "clave_incorrecta")


def test_login_usuario_inactivo_lanza_error(mock_usuarios_deps):
    usuario_repo, hasher, token_service = mock_usuarios_deps
    service = UsuariosService(usuario_repo, hasher, token_service)

    usuario_db = Usuario(
        id=7,
        email="inactivo@example.com",
        activo=False,
        password_hash="hashed_clave",
    )
    usuario_repo.obtener_por_email.return_value = usuario_db
    hasher.verify.return_value = True

    with pytest.raises(InactiveUserError):
        service.login("inactivo@example.com", "clave_correcta")
