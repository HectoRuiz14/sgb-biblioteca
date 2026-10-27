"""Adaptadores de datos abiertos y analítica DuckDB."""
from .adapters import BibliotecasDatosGovAdapter, DaneDivipolaAdapter
from .duckdb_adapter import DuckDBAnalisisAdapter

__all__ = [
    "BibliotecasDatosGovAdapter",
    "DaneDivipolaAdapter",
    "DuckDBAnalisisAdapter",
]
