"""Seguridad sin dependencias externas: hash de contraseñas (PBKDF2-SHA256) y tokens JWT (HS256).
Implementa PasswordHasherPort y TokenPort.
"""
import base64
import hashlib
import hmac
import json
import math
import os
import secrets
import time
from typing import Any, Dict, Optional

from sgb.domain.usuarios.entities import ROLES_VALIDOS, ROL_POR_DEFECTO
from sgb.domain.usuarios.ports import PasswordHasherPort, TokenPort

ITERATIONS = 600_000
TOKEN_MINUTES_DEFAULT = 60


class TokenError(Exception):
    """Token inválido, manipulado o vencido."""


def _secret() -> bytes:
    secret = os.getenv("SECRET_KEY")
    if not secret or secret in {"dev-secret-change-me", "cambia-esto"}:
        raise RuntimeError("Set SECRET_KEY to a unique, random value before using JWT authentication")
    return secret.encode()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---------- contraseñas ----------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64d(salt), int(iters))
        return hmac.compare_digest(calc, _b64d(digest))
    except (ValueError, TypeError):
        return False


# ---------- JWT HS256 ----------
def _sign(signing_input: str) -> str:
    return _b64e(hmac.new(_secret(), signing_input.encode(), hashlib.sha256).digest())


def create_access_token(
    user_id: int,
    minutes: int | None = None,
    roles: list[str] | None = None,
) -> str:
    minutes = TOKEN_MINUTES_DEFAULT if minutes is None else minutes
    roles = [ROL_POR_DEFECTO] if roles is None else list(dict.fromkeys(roles))
    if not roles or any(role not in ROLES_VALIDOS for role in roles):
        raise ValueError(f"roles must be a non-empty subset of {sorted(ROLES_VALIDOS)}")
    now = int(time.time())
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64e(
        json.dumps(
            {"sub": str(user_id), "iat": now, "exp": now + minutes * 60, "roles": roles},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    return f"{signing_input}.{_sign(signing_input)}"


def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature = token.split(".")
        header = json.loads(_b64d(header_b64))
        payload = json.loads(_b64d(payload_b64))
        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise TokenError("Malformed token")
        if header.get("alg") != "HS256":
            raise TokenError("Unsupported algorithm")
        if not hmac.compare_digest(signature, _sign(f"{header_b64}.{payload_b64}")):
            raise TokenError("Invalid signature")
        expiration = payload.get("exp")
        roles = payload.get("roles")
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise TokenError("Invalid subject")
        if (
            isinstance(expiration, bool)
            or not isinstance(expiration, (int, float))
            or not math.isfinite(expiration)
        ):
            raise TokenError("Invalid expiration")
        if expiration <= time.time():
            raise TokenError("Token expired")
        if (
            not isinstance(roles, list)
            or not roles
            or any(not isinstance(role, str) or role not in ROLES_VALIDOS for role in roles)
            or len(roles) != len(set(roles))
        ):
            raise TokenError("Invalid roles claim")
    except TokenError:
        raise
    except (ValueError, TypeError, UnicodeDecodeError) as e:
        raise TokenError("Malformed token") from e
    return payload


class PasswordHasher(PasswordHasherPort):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password: str, stored: Optional[str]) -> bool:
        return verify_password(password, stored)


class JWTTokenService(TokenPort):
    def create_token(
        self,
        user_id: int,
        minutes: Optional[int] = None,
        roles: Optional[list[str]] = None,
    ) -> str:
        return create_access_token(user_id, minutes, roles)

    def decode_token(self, token: str) -> Dict[str, Any]:
        return decode_access_token(token)
