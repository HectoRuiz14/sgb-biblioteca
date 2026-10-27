"""Entidades puras del Bounded Context Catálogo (sin dependencias de BD ni FastAPI)."""
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Autor:
    id: Optional[int] = None
    nombre: str = ""
    nacionalidad: Optional[str] = None
    libros: List["Libro"] = field(default_factory=list, repr=False)
    _orm_model: Optional[Any] = field(default=None, repr=False)

    def __post_init__(self):
        if self.nombre is not None and not str(self.nombre).strip():
            raise ValueError("El nombre del autor no puede estar vacío")
        if self.nombre:
            self.nombre = self.nombre.strip()

    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        if name != "_orm_model" and hasattr(self, "_orm_model") and self._orm_model is not None:
            if hasattr(self._orm_model, name):
                setattr(self._orm_model, name, value)


@dataclass
class Categoria:
    id: Optional[int] = None
    nombre: str = ""
    libros: List["Libro"] = field(default_factory=list, repr=False)
    _orm_model: Optional[Any] = field(default=None, repr=False)

    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        if name != "_orm_model" and hasattr(self, "_orm_model") and self._orm_model is not None:
            if hasattr(self._orm_model, name):
                setattr(self._orm_model, name, value)


@dataclass
class Libro:
    id: Optional[int] = None
    titulo: str = ""
    editorial: Optional[str] = None
    anio: Optional[int] = None
    ejemplares_totales: int = 1
    ejemplares_disponibles: int = 1
    autor_id: Optional[int] = None
    categoria_id: Optional[int] = None
    autor: Optional[Autor] = None
    categoria: Optional[Categoria] = None
    prestamos: List[Any] = field(default_factory=list, repr=False)
    _orm_model: Optional[Any] = field(default=None, repr=False)

    def __post_init__(self):
        if self.ejemplares_disponibles < 0:
            raise ValueError("Los ejemplares disponibles no pueden ser negativos")
        if self.ejemplares_totales < 0:
            raise ValueError("Los ejemplares totales no pueden ser negativos")

    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        if name != "_orm_model" and hasattr(self, "_orm_model") and self._orm_model is not None:
            if hasattr(self._orm_model, name):
                setattr(self._orm_model, name, value)
