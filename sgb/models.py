"""
Modelos ORM del Sistema de Gestión de Biblioteca (SGB) usando SQLAlchemy
(estilo declarativo tipado con Mapped / mapped_column).

Entidades:
    1. Autor
    2. Categoria
    3. Libro
    4. Usuario
    5. Prestamo
"""
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import String, Integer, ForeignKey, Date, Float, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from sgb.database import Base


class Autor(Base):
    __tablename__ = "autores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    nacionalidad: Mapped[Optional[str]] = mapped_column(String(80))

    libros: Mapped[List["Libro"]] = relationship(back_populates="autor")

    @validates("nombre")
    def validar_nombre(self, key, value):
        if not value or not value.strip():
            raise ValueError("El nombre del autor no puede estar vacío")
        return value.strip()


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    libros: Mapped[List["Libro"]] = relationship(back_populates="categoria")


class Libro(Base):
    __tablename__ = "libros"
    __table_args__ = (
        CheckConstraint("ejemplares_totales >= 0", name="ck_ejemplares_totales_no_negativo"),
        CheckConstraint("ejemplares_disponibles >= 0", name="ck_ejemplares_disponibles_no_negativo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    editorial: Mapped[Optional[str]] = mapped_column(String(120))
    anio: Mapped[Optional[int]] = mapped_column(Integer)
    ejemplares_totales: Mapped[int] = mapped_column(Integer, default=1)
    ejemplares_disponibles: Mapped[int] = mapped_column(Integer, default=1)

    autor_id: Mapped[int] = mapped_column(ForeignKey("autores.id"), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)

    autor: Mapped["Autor"] = relationship(back_populates="libros")
    categoria: Mapped["Categoria"] = relationship(back_populates="libros")
    prestamos: Mapped[List["Prestamo"]] = relationship(back_populates="libro")

    @validates("ejemplares_disponibles")
    def validar_disponibles(self, key, value):
        if value < 0:
            raise ValueError("Los ejemplares disponibles no pueden ser negativos")
        return value


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    identificacion: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    tipo_usuario: Mapped[str] = mapped_column(String(20), default="estudiante")
    contacto: Mapped[Optional[str]] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(default=True)

    prestamos: Mapped[List["Prestamo"]] = relationship(back_populates="usuario")

    @validates("tipo_usuario")
    def validar_tipo(self, key, value):
        tipos_validos = {"estudiante", "docente", "externo"}
        if value not in tipos_validos:
            raise ValueError(f"tipo_usuario debe ser uno de {tipos_validos}")
        return value


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_prestamo: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_limite: Mapped[date] = mapped_column(Date)
    fecha_devolucion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    multa: Mapped[float] = mapped_column(Float, default=0.0)

    libro_id: Mapped[int] = mapped_column(ForeignKey("libros.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    libro: Mapped["Libro"] = relationship(back_populates="prestamos")
    usuario: Mapped["Usuario"] = relationship(back_populates="prestamos")

    DIAS_PRESTAMO = {"estudiante": 8, "docente": 15, "externo": 5}
    VALOR_MULTA_DIA = 1000  # pesos por día de retraso

    @staticmethod
    def calcular_fecha_limite(tipo_usuario: str, desde: date = None) -> date:
        desde = desde or date.today()
        dias = Prestamo.DIAS_PRESTAMO.get(tipo_usuario, 8)
        return desde + timedelta(days=dias)

    def calcular_multa(self, fecha_actual: date = None) -> float:
        fecha_actual = fecha_actual or date.today()
        if fecha_actual > self.fecha_limite:
            dias_retraso = (fecha_actual - self.fecha_limite).days
            self.multa = dias_retraso * self.VALOR_MULTA_DIA
        return self.multa