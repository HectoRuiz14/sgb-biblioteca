"""
Repositorios CRUD para el SGB usando SQLAlchemy.
Mapean explícitamente entre modelos ORM de infraestructura y entidades puras de dominio.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from sgb.domain.catalogo.entities import Autor, Categoria, Libro
from sgb.domain.catalogo.ports import LibroRepositoryPort
from sgb.domain.prestamos.entities import Prestamo
from sgb.domain.prestamos.ports import PrestamoRepositoryPort
from sgb.domain.usuarios.entities import Usuario
from sgb.domain.usuarios.ports import UsuarioRepositoryPort
from sgb.infrastructure.models import (
    Autor as AutorModel,
    Categoria as CategoriaModel,
    Libro as LibroModel,
    Prestamo as PrestamoModel,
    Usuario as UsuarioModel,
)


class LibroRepository(LibroRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_domain(model: Optional[LibroModel]) -> Optional[Libro]:
        if model is None:
            return None
        autor_domain = (
            Autor(id=model.autor.id, nombre=model.autor.nombre, nacionalidad=model.autor.nacionalidad)
            if model.autor
            else None
        )
        categoria_domain = (
            Categoria(id=model.categoria.id, nombre=model.categoria.nombre)
            if model.categoria
            else None
        )
        prestamos_list = list(model.prestamos) if hasattr(model, "prestamos") and model.prestamos else []
        return Libro(
            id=model.id,
            titulo=model.titulo,
            editorial=model.editorial,
            anio=model.anio,
            ejemplares_totales=model.ejemplares_totales,
            ejemplares_disponibles=model.ejemplares_disponibles,
            autor_id=model.autor_id,
            categoria_id=model.categoria_id,
            autor=autor_domain,
            categoria=categoria_domain,
            prestamos=prestamos_list,
            _orm_model=model,
        )

    @staticmethod
    def _to_model(entity: Libro | LibroModel) -> LibroModel:
        if isinstance(entity, LibroModel):
            return entity
        return LibroModel(
            id=entity.id,
            titulo=entity.titulo,
            editorial=entity.editorial,
            anio=entity.anio,
            ejemplares_totales=entity.ejemplares_totales,
            ejemplares_disponibles=entity.ejemplares_disponibles,
            autor_id=entity.autor_id,
            categoria_id=entity.categoria_id,
        )

    def crear(self, libro: Libro | LibroModel) -> Libro:
        model = self._to_model(libro)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        # Asegurar carga de relaciones si están presentes
        if model.autor_id and not model.autor:
            model.autor = self.session.get(AutorModel, model.autor_id)
        if model.categoria_id and not model.categoria:
            model.categoria = self.session.get(CategoriaModel, model.categoria_id)
        return self._to_domain(model)

    def obtener(self, libro_id: int) -> Optional[Libro]:
        stmt = (
            select(LibroModel)
            .options(
                joinedload(LibroModel.autor),
                joinedload(LibroModel.categoria),
                joinedload(LibroModel.prestamos),
            )
            .where(LibroModel.id == libro_id)
        )
        model = self.session.scalar(stmt)
        return self._to_domain(model)

    def listar(self) -> List[Libro]:
        models = list(self.session.scalars(select(LibroModel)))
        return [self._to_domain(m) for m in models]

    def actualizar(self, libro_id: int, **campos) -> Optional[Libro]:
        model = self.session.get(LibroModel, libro_id)
        if not model:
            return None
        for clave, valor in campos.items():
            setattr(model, clave, valor)
        self.session.commit()
        self.session.refresh(model)
        return self.obtener(libro_id)

    def eliminar(self, libro_id: int) -> bool:
        model = self.session.get(LibroModel, libro_id)
        if not model:
            return False
        self.session.delete(model)
        self.session.commit()
        return True

    def listar_con_autor(self) -> List[Libro]:
        stmt = select(LibroModel).options(
            joinedload(LibroModel.autor),
            joinedload(LibroModel.categoria),
        )
        models = list(self.session.scalars(stmt).unique())
        return [self._to_domain(m) for m in models]


class UsuarioRepository(UsuarioRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_domain(model: Optional[UsuarioModel]) -> Optional[Usuario]:
        if model is None:
            return None
        return Usuario(
            id=model.id,
            nombre=model.nombre,
            identificacion=model.identificacion,
            tipo_usuario=model.tipo_usuario,
            contacto=model.contacto,
            activo=model.activo,
            email=model.email,
            password_hash=model.password_hash,
            _orm_model=model,
        )

    @staticmethod
    def _to_model(entity: Usuario | UsuarioModel) -> UsuarioModel:
        if isinstance(entity, UsuarioModel):
            return entity
        return UsuarioModel(
            id=entity.id,
            nombre=entity.nombre,
            identificacion=entity.identificacion,
            tipo_usuario=entity.tipo_usuario,
            contacto=entity.contacto,
            activo=entity.activo,
            email=entity.email,
            password_hash=entity.password_hash,
        )

    def crear(self, usuario: Usuario | UsuarioModel) -> Usuario:
        model = self._to_model(usuario)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        model = self.session.get(UsuarioModel, usuario_id)
        return self._to_domain(model)

    def listar(self) -> List[Usuario]:
        models = list(self.session.scalars(select(UsuarioModel)))
        return [self._to_domain(m) for m in models]

    def actualizar(self, usuario_id: int, **campos) -> Optional[Usuario]:
        model = self.session.get(UsuarioModel, usuario_id)
        if not model:
            return None
        for clave, valor in campos.items():
            setattr(model, clave, valor)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def eliminar(self, usuario_id: int) -> bool:
        model = self.session.get(UsuarioModel, usuario_id)
        if not model:
            return False
        self.session.delete(model)
        self.session.commit()
        return True


class PrestamoRepository(PrestamoRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: Optional[PrestamoModel]) -> Optional[Prestamo]:
        if model is None:
            return None
        libro_domain = LibroRepository._to_domain(model.libro) if model.libro else None
        usuario_domain = UsuarioRepository._to_domain(model.usuario) if model.usuario else None
        return Prestamo(
            id=model.id,
            fecha_prestamo=model.fecha_prestamo,
            fecha_limite=model.fecha_limite,
            fecha_devolucion=model.fecha_devolucion,
            multa=model.multa,
            libro_id=model.libro_id,
            usuario_id=model.usuario_id,
            libro=libro_domain,
            usuario=usuario_domain,
            _orm_model=model,
        )

    @staticmethod
    def _to_model(entity: Prestamo | PrestamoModel) -> PrestamoModel:
        if isinstance(entity, PrestamoModel):
            return entity
        return PrestamoModel(
            id=entity.id,
            fecha_prestamo=entity.fecha_prestamo,
            fecha_limite=entity.fecha_limite,
            fecha_devolucion=entity.fecha_devolucion,
            multa=entity.multa,
            libro_id=entity.libro_id,
            usuario_id=entity.usuario_id,
        )

    def crear(self, libro_id: int, usuario_id: int) -> Prestamo:
        usuario = self.session.get(UsuarioModel, usuario_id)
        libro = self.session.get(LibroModel, libro_id)
        if not usuario or not libro:
            raise ValueError("Libro o usuario no existe")
        if libro.ejemplares_disponibles < 1:
            raise ValueError("No hay ejemplares disponibles para préstamo")

        fecha_limite = Prestamo.calcular_fecha_limite(usuario.tipo_usuario)
        prestamo = PrestamoModel(
            libro_id=libro_id,
            usuario_id=usuario_id,
            fecha_prestamo=date.today(),
            fecha_limite=fecha_limite,
        )
        libro.ejemplares_disponibles -= 1
        self.session.add(prestamo)
        self.session.commit()
        self.session.refresh(prestamo)
        return self._to_domain(prestamo)

    def obtener(self, prestamo_id: int) -> Optional[Prestamo]:
        model = self.session.get(PrestamoModel, prestamo_id)
        return self._to_domain(model)

    def listar(self) -> List[Prestamo]:
        models = list(self.session.scalars(select(PrestamoModel)))
        return [self._to_domain(m) for m in models]

    def registrar_devolucion(self, prestamo_id: int) -> Optional[Prestamo]:
        model = self.session.get(PrestamoModel, prestamo_id)
        if not model:
            return None
        model.fecha_devolucion = date.today()
        # Regla de cálculo de multa pura delegada a la entidad de dominio
        domain_prestamo = self._to_domain(model)
        model.multa = domain_prestamo.calcular_multa(model.fecha_devolucion)
        model.libro.ejemplares_disponibles += 1
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def eliminar(self, prestamo_id: int) -> bool:
        model = self.session.get(PrestamoModel, prestamo_id)
        if not model:
            return False
        self.session.delete(model)
        self.session.commit()
        return True

    def historial_por_usuario(self, usuario_id: int) -> List[Prestamo]:
        stmt = (
            select(PrestamoModel)
            .options(joinedload(PrestamoModel.libro))
            .where(PrestamoModel.usuario_id == usuario_id)
        )
        models = list(self.session.scalars(stmt).unique())
        return [self._to_domain(m) for m in models]
