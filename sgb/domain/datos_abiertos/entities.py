"""Entidades puras del Bounded Context Datos Abiertos."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BibliotecaPublica:
    nombre: str
    municipio: str
    correo: Optional[str] = None
    telefono: Optional[str] = None


@dataclass(frozen=True)
class MunicipioDivipola:
    codigo_departamento: str
    departamento: str
    codigo_municipio: str
    municipio: str
    tipo: str
    longitud: Optional[str] = None
    latitud: Optional[str] = None
