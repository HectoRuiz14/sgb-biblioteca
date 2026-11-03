import time

import pytest

from sgb.infrastructure.security import TokenError, create_access_token, decode_access_token, hash_password, verify_password


def test_hash_y_verificacion():
    h = hash_password("Secreta123")
    assert h != "Secreta123" and h.startswith("pbkdf2_sha256$")
    assert verify_password("Secreta123", h) and not verify_password("otra", h)
    assert hash_password("Secreta123") != h  # sal aleatoria
    assert not verify_password("x", None) and not verify_password("x", "basura")


def test_token_ida_y_vuelta():
    payload = decode_access_token(create_access_token(7, roles=["ADMIN"]))
    assert payload["sub"] == "7"
    assert payload["roles"] == ["ADMIN"]


def test_token_manipulado_o_vencido():
    token = create_access_token(7)
    h, p, s = token.split(".")
    with pytest.raises(TokenError):
        decode_access_token(f"{h}.{p}.{s[:-2]}aa")
    with pytest.raises(TokenError):
        decode_access_token("no-es-un-token")
    with pytest.raises(TokenError):
        decode_access_token(create_access_token(7, minutes=-1))


@pytest.mark.parametrize("secret", [None, "dev-secret-change-me", "cambia-esto"])
def test_jwt_rechaza_clave_ausente_o_de_ejemplo(monkeypatch, secret):
    if secret is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", secret)

    with pytest.raises(RuntimeError, match="Set SECRET_KEY"):
        create_access_token(7)
