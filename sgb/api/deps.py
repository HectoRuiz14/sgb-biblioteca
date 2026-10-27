"""Inyección y ensamblado de dependencias para FastAPI."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from sgb.application.asistente_service import AsistenteService
from sgb.application.catalogo_service import CatalogoService
from sgb.application.prestamos_service import PrestamosService
from sgb.application.usuarios_service import UsuariosService
from sgb.domain.usuarios.entities import Usuario
from sgb.infrastructure.database import get_session
from sgb.infrastructure.llm import GeminiLLMClient
from sgb.infrastructure.rag import KeywordRAGRetriever
from sgb.infrastructure.repositories import (
    AutorRepository,
    CategoriaRepository,
    LibroRepository,
    PrestamoRepository,
    SQLAlchemyUnitOfWork,
    UsuarioRepository,
)
from sgb.infrastructure.security import (
    JWTTokenService,
    PasswordHasher,
    TokenError,
    decode_access_token,
)

bearer = HTTPBearer(auto_error=False, description="Paste the JWT returned by /api/v1/auth/login")


def get_catalogo_service(session: Session = Depends(get_session)) -> CatalogoService:
    return CatalogoService(
        libro_repo=LibroRepository(session),
        autor_repo=AutorRepository(session),
        categoria_repo=CategoriaRepository(session),
    )


def get_usuarios_service(session: Session = Depends(get_session)) -> UsuariosService:
    return UsuariosService(
        usuario_repo=UsuarioRepository(session),
        password_hasher=PasswordHasher(),
        token_service=JWTTokenService(),
    )


def get_prestamos_service(session: Session = Depends(get_session)) -> PrestamosService:
    return PrestamosService(
        prestamo_repo=PrestamoRepository(session),
        libro_repo=LibroRepository(session),
        usuario_repo=UsuarioRepository(session),
        uow=SQLAlchemyUnitOfWork(session),
    )


def get_asistente_service(session: Session = Depends(get_session)) -> AsistenteService:
    return AsistenteService(
        llm_port=GeminiLLMClient(),
        retriever_port=KeywordRAGRetriever(session),
    )


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    service: UsuariosService = Depends(get_usuarios_service),
) -> Usuario:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if cred is None:
        raise unauthorized
    try:
        payload = decode_access_token(cred.credentials)
        user = service.obtener_por_id(int(payload["sub"]))
    except (TokenError, KeyError, ValueError):
        raise unauthorized
    if user is None or not user.activo:
        raise unauthorized
    return user
