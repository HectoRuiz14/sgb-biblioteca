from fastapi import APIRouter, Depends, HTTPException, status

from sgb.api.deps import get_current_user, get_usuarios_service
from sgb.api.schemas import ErrorOut, LoginIn, RegisterIn, TokenOut, UsuarioOut
from sgb.application.usuarios_service import UsuariosService
from sgb.domain.exceptions import (
    EmailAlreadyRegisteredError,
    IdentificacionAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from sgb.domain.usuarios.entities import Usuario

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user account. Email and national ID must be unique. The password is stored hashed (PBKDF2-SHA256).",
    responses={409: {"model": ErrorOut, "description": "Email or ID already registered"}},
)
def register(
    data: RegisterIn,
    service: UsuariosService = Depends(get_usuarios_service),
):
    try:
        return service.register(
            nombre=data.nombre,
            identificacion=data.identificacion,
            email=data.email,
            password=data.password,
            tipo_usuario=data.tipo_usuario,
            contacto=data.contacto,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    except IdentificacionAlreadyRegisteredError:
        raise HTTPException(status.HTTP_409_CONFLICT, "National ID already registered")
    except UserAlreadyExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or national ID already registered")


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Log in",
    description="Validates email and password and returns a JWT access token (valid for 60 minutes).",
    responses={
        401: {"model": ErrorOut, "description": "Invalid credentials"},
        403: {"model": ErrorOut, "description": "Inactive account"},
    },
)
def login(
    data: LoginIn,
    service: UsuariosService = Depends(get_usuarios_service),
):
    try:
        token, usuario = service.login(data.email, data.password)
        return TokenOut(access_token=token, usuario=UsuarioOut.model_validate(usuario))
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    except InactiveUserError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Current user",
    description="Returns the profile of the authenticated user.",
    responses={401: {"model": ErrorOut, "description": "Missing or invalid token"}},
)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario
