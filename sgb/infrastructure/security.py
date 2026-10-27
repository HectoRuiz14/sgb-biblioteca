"""Seguridad sin dependencias externas: hash de contraseñas (PBKDF2-SHA256) y tokens JWT (HS256).
Implementa PasswordHasherPort y TokenPort.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional

from sgb.domain.usuarios.ports import PasswordHasherPort, TokenPort

ITERATIONS = 600_000
TOKEN_MINUTES_DEFAULT = 60


class TokenError(Exception):
    """Token inválido, manipulado o vencido."""


def _secret() -> bytes:
    return os.getenv("SECRET_KEY", "dev-secret-change-me").encode()


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


def create_access_token(user_id: int, minutes: int | None = None) -> str:
    minutes = TOKEN_MINUTES_DEFAULT if minutes is None else minutes
    now = int(time.time())
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64e(json.dumps({"sub": str(user_id), "iat": now, "exp": now + minutes * 60}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    return f"{signing_input}.{_sign(signing_input)}"


def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{header_b64}.{payload_b64}")):
            raise TokenError("Invalid signature")
        if json.loads(_b64d(header_b64)).get("alg") != "HS256":
            raise TokenError("Unsupported algorithm")
        payload = json.loads(_b64d(payload_b64))
    except TokenError:
        raise
    except Exception as e:  # formato roto
        raise TokenError("Malformed token") from e
    if payload.get("exp", 0) < time.time():
        raise TokenError("Token expired")
    return payload


class PasswordHasher(PasswordHasherPort):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password: str, stored: Optional[str]) -> bool:
        return verify_password(password, stored)


class JWTTokenService(TokenPort):
    def create_token(self, user_id: int, minutes: Optional[int] = None) -> str:
        return create_access_token(user_id, minutes)

    def decode_token(self, token: str) -> Dict[str, Any]:
        return decode_access_token(token)
