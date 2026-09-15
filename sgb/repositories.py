"""
Repositorios CRUD para el SGB.
Incluye una consulta con JOIN (listar_con_autor) que trae libro, autor y
categoria en una sola query en lugar de disparar una consulta extra por
cada relación accedida.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from sgb.models import Libro, Usuario, Prestamo, Autor, Categoria


class LibroRepository:
    def __init__(self, session: Session):
        self.session = session

    def crear(self, libro: Libro) -> Libro:
        self.session.add(libro)
        self.session.commit()
        self.session.refresh(libro)
        return libro

    def obtener(self, libro_id: int) -> Optional[Libro]:
        return self.session.get(Libro, libro_id)

    def listar(self) -> List[Libro]:
        return list(self.session.scalars(select(Libro)))

    def actualizar(self, libro_id: int, **campos) -> Optional[Libro]:
        libro = self.obtener(libro_id)
        if not libro:
            return None
        for clave, valor in campos.items():
            setattr(libro, clave, valor)
        self.session.commit()
        self.session.refresh(libro)
        return libro

    def eliminar(self, libro_id: int) -> bool:
        libro = self.obtener(libro_id)
        if not libro:
            return False
        self.session.delete(libro)
        self.session.commit()
        return True

    def listar_con_autor(self) -> List[Libro]:
        stmt = select(Libro).options(
            joinedload(Libro.autor),
            joinedload(Libro.categoria),
        )
        return list(self.session.scalars(stmt).unique())


class UsuarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def crear(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        self.session.commit()
        self.session.refresh(usuario)
        return usuario

    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        return self.session.get(Usuario, usuario_id)

    def listar(self) -> List[Usuario]:
        return list(self.session.scalars(select(Usuario)))

    def actualizar(self, usuario_id: int, **campos) -> Optional[Usuario]:
        usuario = self.obtener(usuario_id)
        if not usuario:
            return None
        for clave, valor in campos.items():
            setattr(usuario, clave, valor)
        self.session.commit()
        self.session.refresh(usuario)
        return usuario

    def eliminar(self, usuario_id: int) -> bool:
        usuario = self.obtener(usuario_id)
        if not usuario:
            return False
        self.session.delete(usuario)
        self.session.commit()
        return True


class PrestamoRepository:
    def __init__(self, session: Session):
        self.session = session

    def crear(self, libro_id: int, usuario_id: int) -> Prestamo:
        usuario = self.session.get(Usuario, usuario_id)
        libro = self.session.get(Libro, libro_id)
        if not usuario or not libro:
            raise ValueError("Libro o usuario no existe")
        if libro.ejemplares_disponibles < 1:
            raise ValueError("No hay ejemplares disponibles para préstamo")

        prestamo = Prestamo(
            libro_id=libro_id,
            usuario_id=usuario_id,
            fecha_prestamo=date.today(),
            fecha_limite=Prestamo.calcular_fecha_limite(usuario.tipo_usuario),
        )
        libro.ejemplares_disponibles -= 1
        self.session.add(prestamo)
        self.session.commit()
        self.session.refresh(prestamo)
        return prestamo

    def obtener(self, prestamo_id: int) -> Optional[Prestamo]:
        return self.session.get(Prestamo, prestamo_id)

    def listar(self) -> List[Prestamo]:
        return list(self.session.scalars(select(Prestamo)))

    def registrar_devolucion(self, prestamo_id: int) -> Optional[Prestamo]:
        prestamo = self.obtener(prestamo_id)
        if not prestamo:
            return None
        prestamo.fecha_devolucion = date.today()
        prestamo.calcular_multa(prestamo.fecha_devolucion)
        prestamo.libro.ejemplares_disponibles += 1
        self.session.commit()
        self.session.refresh(prestamo)
        return prestamo

    def eliminar(self, prestamo_id: int) -> bool:
        prestamo = self.obtener(prestamo_id)
        if not prestamo:
            return False
        self.session.delete(prestamo)
        self.session.commit()
        return True

    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        stmt = (
            select(Prestamo)
            .options(joinedload(Prestamo.libro))
            .where(Prestamo.usuario_id == usuario_id)
        )
        return list(self.session.scalars(stmt).unique())