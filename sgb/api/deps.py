from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from sgb.infrastructure.database import get_session
from sgb.infrastructure.models import Usuario
from sgb.infrastructure.security import TokenError, decode_access_token

bearer = HTTPBearer(auto_error=False, description="Paste the JWT returned by /api/v1/auth/login")


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                     session: Session = Depends(get_session)) -> Usuario:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if cred is None:
        raise unauthorized
    try:
        payload = decode_access_token(cred.credentials)
        user = session.get(Usuario, int(payload["sub"]))
    except (TokenError, KeyError, ValueError):
        raise unauthorized
    if user is None or not user.activo:
        raise unauthorized
    return user
