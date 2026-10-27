"""Entidades puras del Bounded Context Datos Abiertos."""
from dataclasses import dataclass
from typing import List, Optional


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


@dataclass(frozen=True)
class MunicipioConteo:
    municipio: str
    total_bibliotecas: int


@dataclass(frozen=True)
class DepartamentoConteo:
    departamento: str
    total_bibliotecas: int


@dataclass(frozen=True)
class EstadisticasDescriptivas:
    media: float
    mediana: float
    minimo: int
    maximo: int


@dataclass(frozen=True)
class EstadisticasBibliotecas:
    total_bibliotecas: int
    total_municipios_con_biblioteca: int
    porcentaje_con_correo: float
    top_municipios: List[MunicipioConteo]


@dataclass(frozen=True)
class CruceDivipolaResultado:
    bibliotecas_por_departamento: List[DepartamentoConteo]
    total_municipios_divipola: int
    municipios_sin_biblioteca: int
    estadisticas_distribucion: EstadisticasDescriptivas
