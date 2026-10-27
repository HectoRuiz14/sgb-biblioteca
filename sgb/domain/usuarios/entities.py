"""Entidad pura del Bounded Context Usuarios."""
from dataclasses import dataclass, field
from typing import Any, List, Optional

TIPOS_USUARIO_VALIDOS = {"estudiante", "docente", "externo"}


@dataclass
class Usuario:
    id: Optional[int] = None
    nombre: str = ""
    identificacion: str = ""
    tipo_usuario: str = "estudiante"
    contacto: Optional[str] = None
    activo: bool = True
    email: Optional[str] = None
    password_hash: Optional[str] = None
    prestamos: List[Any] = field(default_factory=list, repr=False)
    _orm_model: Optional[Any] = field(default=None, repr=False)

    def __post_init__(self):
        if self.tipo_usuario not in TIPOS_USUARIO_VALIDOS:
            raise ValueError(f"tipo_usuario debe ser uno de {TIPOS_USUARIO_VALIDOS}")

    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        if name != "_orm_model" and hasattr(self, "_orm_model") and self._orm_model is not None:
            if hasattr(self._orm_model, name):
                setattr(self._orm_model, name, value)
