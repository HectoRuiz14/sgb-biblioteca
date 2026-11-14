"""
Configuración central de SQLAlchemy: engine, sesión y clase base declarativa.
La conexión se configura con la variable de entorno DATABASE_URL.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL es obligatoria.")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# SQL_ECHO=1 en el entorno para ver las consultas SQL
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "0") == "1",
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""
    pass


def get_session():
    """Generador de sesión, útil para usar con 'with' o dependencias."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Crea todas las tablas directamente (para desarrollo rápido; en
    producción se usa Alembic para versionar el esquema)."""
    Base.metadata.create_all(bind=engine)
