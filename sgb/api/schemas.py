"""Esquemas Pydantic (entrada/salida de la API). Textos de documentación en inglés (OpenAPI)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TipoUsuario = Literal["estudiante", "docente", "externo"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------- auth ----------
class RegisterIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120, description="Full name", examples=["Ana Torres"])
    identificacion: str = Field(..., min_length=3, max_length=30, description="National ID (unique)", examples=["1001234567"])
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=120, description="Email, used to log in", examples=["ana@example.com"])
    password: str = Field(..., min_length=8, max_length=72, description="Password (min. 8 characters)", examples=["Secreta123"])
    tipo_usuario: TipoUsuario = Field("estudiante", description="User type: estudiante, docente or externo")
    contacto: Optional[str] = Field(None, max_length=120, description="Phone or other contact", examples=["3001234567"])


class LoginIn(BaseModel):
    email: str = Field(..., examples=["ana@example.com"])
    password: str = Field(..., examples=["Secreta123"])


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., examples=[1])
    nombre: str
    identificacion: str
    email: Optional[str] = None
    tipo_usuario: str
    activo: bool


class TokenOut(BaseModel):
    access_token: str = Field(..., description="JWT to send as 'Authorization: Bearer <token>'")
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---------- libros ----------
class LibroIn(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200, description="Book title", examples=["Cien años de soledad"])
    autor: str = Field(..., min_length=1, max_length=120, description="Author name (created if it does not exist)", examples=["Gabriel García Márquez"])
    categoria: str = Field(..., min_length=1, max_length=60, description="Category name (created if it does not exist)", examples=["Novela"])
    editorial: Optional[str] = Field(None, max_length=120, examples=["Sudamericana"])
    anio: Optional[int] = Field(None, ge=1000, le=2100, description="Publication year", examples=[1967])
    ejemplares_totales: int = Field(1, ge=0, description="Total number of copies owned", examples=[3])


class LibroOut(BaseModel):
    id: int
    titulo: str
    autor: str
    categoria: str
    editorial: Optional[str] = None
    anio: Optional[int] = None
    ejemplares_totales: int
    ejemplares_disponibles: int = Field(..., description="Copies not currently on loan")


class ErrorOut(BaseModel):
    detail: str = Field(..., examples=["Book with id 99 not found"])


# ---------- IA ----------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="Question in natural language",
                          examples=["Which books do you have by García Márquez?"])
    technique: str = Field("zero-shot", pattern="^(zero-shot|few-shot|cot)$",
                           description="Prompting technique: zero-shot, few-shot or cot (chain-of-thought)")


class AskResponse(BaseModel):
    answer: str
    technique: str
    model: str
    prompt_tokens: int = Field(..., description="Input tokens reported by the LLM API")
    completion_tokens: int = Field(..., description="Output tokens reported by the LLM API")
    latency_ms: int
    sources: list[int] = Field(..., description="IDs of the books retrieved as context (RAG)")


# ---------- Datos Abiertos y Analítica DuckDB ----------
class MunicipioConteoOut(BaseModel):
    municipio: str
    total_bibliotecas: int


class DepartamentoConteoOut(BaseModel):
    departamento: str
    total_bibliotecas: int


class EstadisticasDescriptivasOut(BaseModel):
    media: float
    mediana: float
    minimo: int
    maximo: int


class EstadisticasBibliotecasOut(BaseModel):
    total_bibliotecas: int
    total_municipios_con_biblioteca: int
    porcentaje_con_correo: float
    top_municipios: List[MunicipioConteoOut]


class CruceDivipolaOut(BaseModel):
    bibliotecas_por_departamento: List[DepartamentoConteoOut]
    total_municipios_divipola: int = Field(
        ...,
        description="Total de municipios en DIVIPOLA pertenecientes a los departamentos cubiertos por el dataset",
    )
    municipios_sin_biblioteca: int = Field(
        ...,
        description="Municipios sin biblioteca registrada dentro de los departamentos cubiertos",
    )
    estadisticas_distribucion: EstadisticasDescriptivasOut


class EstadoCircuitosOut(BaseModel):
    bibliotecas: str
    divipola: str
