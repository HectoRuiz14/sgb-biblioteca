"""Pruebas de integración de la API (Guía 5). El LLM se simula: no consume cuota ni requiere internet."""
import time

import pytest

from sgb.infrastructure import llm
from sgb.infrastructure.repositories import PrestamoRepository
from sgb.infrastructure.models import Usuario
from sgb.infrastructure.security import create_access_token
from tests.conftest import USUARIO

LIBRO = {"titulo": "Cien años de soledad", "autor": "Gabriel García Márquez", "categoria": "Novela",
         "editorial": "Sudamericana", "anio": 1967, "ejemplares_totales": 3}


# ===== Integración 1: registro + login + perfil =====
def test_registro_login_y_perfil(client):
    r = client.post("/api/v1/auth/register", json=USUARIO)
    assert r.status_code == 201 and "password" not in r.text and "password_hash" not in r.text

    # duplicados -> 409
    assert client.post("/api/v1/auth/register", json=USUARIO).status_code == 409
    assert client.post("/api/v1/auth/register", json={**USUARIO, "email": "otro@example.com"}).status_code == 409  # misma identificación

    # credenciales incorrectas -> 401
    assert client.post("/api/v1/auth/login", json={"email": USUARIO["email"], "password": "mala"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "nadie@example.com", "password": "x"}).status_code == 401

    ok = client.post("/api/v1/auth/login", json={"email": "ANA@example.com", "password": USUARIO["password"]})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == USUARIO["email"]


# ===== Integración 2: CRUD completo de libros protegido por token =====
def test_crud_libros(client, auth_headers):
    assert client.get("/api/v1/libros").status_code == 401  # sin token

    r = client.post("/api/v1/libros", json=LIBRO, headers=auth_headers)
    assert r.status_code == 201
    libro = r.json()
    assert libro["autor"] == LIBRO["autor"] and libro["ejemplares_disponibles"] == 3

    lid = libro["id"]
    assert client.get(f"/api/v1/libros/{lid}", headers=auth_headers).json()["titulo"] == LIBRO["titulo"]
    assert len(client.get("/api/v1/libros?q=cien", headers=auth_headers).json()) == 1
    assert client.get("/api/v1/libros?categoria=Otra", headers=auth_headers).json() == []

    upd = client.put(f"/api/v1/libros/{lid}", json={**LIBRO, "editorial": "Oveja Negra", "ejemplares_totales": 5}, headers=auth_headers)
    assert upd.status_code == 200
    assert upd.json()["editorial"] == "Oveja Negra" and upd.json()["ejemplares_disponibles"] == 5

    assert client.delete(f"/api/v1/libros/{lid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/libros/{lid}", headers=auth_headers).status_code == 404


# ===== Integración 3: manejo de errores HTTP =====
def test_errores_http(client, auth_headers):
    assert client.get("/api/v1/libros/999", headers=auth_headers).status_code == 404
    assert client.delete("/api/v1/libros/999", headers=auth_headers).status_code == 404
    assert client.post("/api/v1/libros", json={"titulo": ""}, headers=auth_headers).status_code == 422
    assert client.get("/api/v1/libros?limit=0", headers=auth_headers).status_code == 422
    assert client.post("/api/v1/auth/register", json={**USUARIO, "password": "corta"}).status_code == 422
    assert client.get("/api/v1/libros", headers={"Authorization": "Bearer token.falso.xx"}).status_code == 401

    # libro con préstamos no se puede borrar (409); no se puede bajar el total por debajo de lo prestado
    lid = client.post("/api/v1/libros", json={**LIBRO, "ejemplares_totales": 1}, headers=auth_headers).json()["id"]
    with client.session_factory() as s:
        uid = s.query(Usuario).first().id
        PrestamoRepository(s).crear(libro_id=lid, usuario_id=uid)
    assert client.delete(f"/api/v1/libros/{lid}", headers=auth_headers).status_code == 409
    assert client.put(f"/api/v1/libros/{lid}", json={**LIBRO, "ejemplares_totales": 0}, headers=auth_headers).status_code == 409


# ===== IA: RAG + errores del LLM =====
def test_ia_usa_rag_y_llm(client, auth_headers, monkeypatch):
    client.post("/api/v1/libros", json=LIBRO, headers=auth_headers)
    client.post("/api/v1/libros", json={"titulo": "Clean Code", "autor": "Robert Martin", "categoria": "Software"}, headers=auth_headers)
    capturado = {}

    def falso(prompt):
        capturado["prompt"] = prompt
        return llm.LLMResult("Yes, we have it.", 100, 10, 50, "fake")

    monkeypatch.setattr(llm, "generate", falso)
    r = client.post("/api/v1/ai/ask", json={"question": "Do you have books by Márquez?", "technique": "few-shot"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["sources"] == [1]
    assert "Cien años de soledad" in capturado["prompt"] and "Clean Code" not in capturado["prompt"]
    assert client.post("/api/v1/ai/ask", json={"question": "hola libros"}).status_code == 401  # requiere login


@pytest.mark.parametrize("exc,codigo", [(llm.LLMTimeout("t"), 504), (llm.LLMRateLimit("r"), 429), (llm.LLMUnavailable("u"), 502)])
def test_ia_errores_llm(client, auth_headers, monkeypatch, exc, codigo):
    def falla(prompt):
        raise exc

    monkeypatch.setattr(llm, "generate", falla)
    r = client.post("/api/v1/ai/ask", json={"question": "any books?"}, headers=auth_headers)
    assert r.status_code == codigo


def test_openapi(client):
    spec = client.get("/openapi.json").json()
    assert spec["openapi"].startswith("3.")
    for path in ("/api/v1/auth/login", "/api/v1/libros/{libro_id}", "/api/v1/ai/ask"):
        assert path in spec["paths"]
