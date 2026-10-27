from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sgb.api.deps import get_current_user
from sgb.infrastructure.database import get_session
from sgb.infrastructure.models import Usuario
from sgb.infrastructure.repositories import UsuarioRepository
from sgb.schemas import ErrorOut, LoginIn, RegisterIn, TokenOut, UsuarioOut
from sgb.infrastructure.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED,
             summary="Register a new user",
             description="Creates a user account. Email and national ID must be unique. The password is stored hashed (PBKDF2-SHA256).",
             responses={409: {"model": ErrorOut, "description": "Email or ID already registered"}})
def register(data: RegisterIn, session: Session = Depends(get_session)):
    email = data.email.strip().lower()
    if session.scalar(select(Usuario).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if session.scalar(select(Usuario).where(Usuario.identificacion == data.identificacion)):
        raise HTTPException(status.HTTP_409_CONFLICT, "National ID already registered")
    usuario = Usuario(nombre=data.nombre, identificacion=data.identificacion, email=email,
                      tipo_usuario=data.tipo_usuario, contacto=data.contacto,
                      password_hash=hash_password(data.password))
    try:
        return UsuarioRepository(session).crear(usuario)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or national ID already registered")


@router.post("/login", response_model=TokenOut, summary="Log in",
             description="Validates email and password and returns a JWT access token (valid for 60 minutes).",
             responses={401: {"model": ErrorOut, "description": "Invalid credentials"},
                        403: {"model": ErrorOut, "description": "Inactive account"}})
def login(data: LoginIn, session: Session = Depends(get_session)):
    usuario = session.scalar(select(Usuario).where(Usuario.email == data.email.strip().lower()))
    if usuario is None or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")
    return TokenOut(access_token=create_access_token(usuario.id), usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut, summary="Current user",
            description="Returns the profile of the authenticated user.",
            responses={401: {"model": ErrorOut, "description": "Missing or invalid token"}})
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario
