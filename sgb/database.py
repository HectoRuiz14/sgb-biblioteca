"""
Configuración central de SQLAlchemy: engine, sesión y clase base declarativa.
Usa SQLite por defecto. La URL se puede sobreescribir con la variable de
entorno DATABASE_URL (por ejemplo sqlite:///:memory: para pruebas).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///biblioteca.db")

engine = create_engine(DATABASE_URL, echo=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


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