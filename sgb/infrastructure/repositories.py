"""
Repositorios CRUD para el SGB usando SQLAlchemy.
Mapean explícitamente entre modelos ORM de infraestructura y entidades puras de dominio.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from sgb.domain.catalogo.entities import Autor, Categoria, Libro
from sgb.domain.catalogo.ports import (
    AutorRepositoryPort,
    CategoriaRepositoryPort,
    LibroRepositoryPort,
)
from sgb.domain.exceptions import PrestamoNotFoundError
from sgb.domain.prestamos.entities import Prestamo
from sgb.domain.prestamos.ports import PrestamoRepositoryPort, UnitOfWorkPort
from sgb.domain.usuarios.entities import Usuario
from sgb.domain.usuarios.ports import UsuarioRepositoryPort
from sgb.infrastructure.models import (
    Autor as AutorModel,
    Categoria as CategoriaModel,
    Libro as LibroModel,
    Prestamo as PrestamoModel,
    Usuario as UsuarioModel,
)


class SQLAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session: Session):
        self.session = session

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class AutorRepository(AutorRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_domain(model: Optional[AutorModel]) -> Optional[Autor]:
        if model is None:
            return None
        return Autor(
            id=model.id,
            nombre=model.nombre,
            nacionalidad=model.nacionalidad,
            _orm_model=model,
        )

    @staticmethod
    def _to_model(entity: Autor | AutorModel) -> AutorModel:
        if isinstance(entity, AutorModel):
            return entity
        return AutorModel(
            id=entity.id,
            nombre=entity.nombre,
            nacionalidad=entity.nacionalidad,
        )

    def obtener_por_nombre(self, nombre: str) -> Optional[Autor]:
        model = self.session.scalar(select(AutorModel).where(AutorModel.nombre == nombre.strip()))
        return self._to_domain(model)

    def crear(self, autor: Autor | AutorModel) -> Autor:
        model = self._to_model(autor)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def obtener_o_crear(self, nombre: str) -> Autor:
        nombre = nombre.strip()
        model = self.session.scalar(select(AutorModel).where(AutorModel.nombre == nombre))
        if model is None:
            model = AutorModel(nombre=nombre)
            self.session.add(model)
            self.session.flush()
            self.session.commit()
            self.session.refresh(model)
        return self._to_domain(model)


class CategoriaRepository(CategoriaRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_domain(model: Optional[CategoriaModel]) -> Optional[Categoria]:
        if model is None:
            return None
        return Categoria(
            id=model.id,
            nombre=model.nombre,
            _orm_model=model,
        )

    @staticmethod
    def _to_model(entity: Categoria | CategoriaModel) -> CategoriaModel:
        if isinstance(entity, CategoriaModel):
            return entity
        return CategoriaModel(
            id=entity.id,
            nombre=entity.nombre,
        )

    def obtener_por_nombre(self, nombre: str) -> Optional[Categoria]:
        model = self.session.scalar(select(CategoriaModel).where(CategoriaModel.nombre == nombre.strip()))
        return self._to_domain(model)

    def crear(self, categoria: Categoria | CategoriaModel) -> Categoria:
        model = self._to_model(categoria)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def obtener_o_crear(self, nombre: str) -> Categoria:
        nombre = nombre.strip()
        model = self.session.scalar(select(CategoriaModel).where(CategoriaModel.nombre == nombre))
        if model is None:
            model = CategoriaModel(nombre=nombre)
            self.session.add(model)
            self.session.flush()
            self.session.commit()
            self.session.refresh(model)
        return self._to_domain(model)


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

    def actualizar(self, libro_id: int, commit: bool = True, **campos) -> Optional[Libro]:
        model = self.session.get(LibroModel, libro_id)
        if not model:
            return None
        for clave, valor in campos.items():
            setattr(model, clave, valor)
        if commit:
            self.session.commit()
            self.session.refresh(model)
        else:
            self.session.flush()
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

    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        model = self.session.scalar(select(UsuarioModel).where(UsuarioModel.email == email.strip().lower()))
        return self._to_domain(model)

    def obtener_por_identificacion(self, identificacion: str) -> Optional[Usuario]:
        model = self.session.scalar(select(UsuarioModel).where(UsuarioModel.identificacion == identificacion.strip()))
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

    @staticmethod
    def _to_domain(model: Optional[PrestamoModel]) -> Optional[Prestamo]:
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
        )

    def agregar(self, prestamo: Prestamo, commit: bool = True) -> Prestamo:
        model = PrestamoModel(
            libro_id=prestamo.libro_id,
            usuario_id=prestamo.usuario_id,
            fecha_prestamo=prestamo.fecha_prestamo,
            fecha_limite=prestamo.fecha_limite,
            fecha_devolucion=prestamo.fecha_devolucion,
            multa=prestamo.multa,
        )
        self.session.add(model)
        if commit:
            self.session.commit()
            self.session.refresh(model)
        else:
            self.session.flush()
            self.session.refresh(model)
        return self._to_domain(model)

    def guardar(self, prestamo: Prestamo, commit: bool = True) -> Prestamo:
        model = self.session.get(PrestamoModel, prestamo.id)
        if not model:
            raise PrestamoNotFoundError(f"Prestamo with id {prestamo.id} not found")
        model.fecha_prestamo = prestamo.fecha_prestamo
        model.fecha_limite = prestamo.fecha_limite
        model.fecha_devolucion = prestamo.fecha_devolucion
        model.multa = prestamo.multa
        if commit:
            self.session.commit()
            self.session.refresh(model)
        else:
            self.session.flush()
            self.session.refresh(model)
        return self._to_domain(model)

    def obtener(self, prestamo_id: int) -> Optional[Prestamo]:
        model = self.session.get(PrestamoModel, prestamo_id)
        return self._to_domain(model)

    def listar(self) -> List[Prestamo]:
        models = list(self.session.scalars(select(PrestamoModel)))
        return [self._to_domain(m) for m in models]

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
