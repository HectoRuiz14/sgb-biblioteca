"""Fixtures compartidas: base SQLite en memoria + cliente HTTP de FastAPI + usuario autenticado."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sgb.infrastructure.models  # noqa: F401  (registra las tablas en Base.metadata)
from sgb.infrastructure.database import Base, get_session
from sgb.main import app

USUARIO = {"nombre": "Ana Torres", "identificacion": "1001", "email": "ana@example.com",
           "password": "Secreta123", "tipo_usuario": "estudiante"}


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = Testing()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = override
    c = TestClient(app)
    c.session_factory = Testing
    yield c
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def auth_headers(client):
    assert client.post("/api/v1/auth/register", json=USUARIO).status_code == 201
    r = client.post("/api/v1/auth/login", json={"email": USUARIO["email"], "password": USUARIO["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
