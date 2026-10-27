"""Puertos (interfaces abstractas) para el Bounded Context Asistente IA."""
from abc import ABC, abstractmethod
from typing import Any, List

from .entities import LLMResult


class LLMPort(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> LLMResult:
        """Envía un prompt al modelo LLM y retorna el resultado."""
        pass


class RetrieverPort(ABC):
    @abstractmethod
    def retrieve(self, session: Any, question: str, k: int = 5) -> List[Any]:
        """Recupera los libros más relevantes dado un texto de consulta."""
        pass

    @abstractmethod
    def format_context(self, libros: List[Any]) -> str:
        """Formatea los libros recuperados como texto de contexto para el LLM."""
        pass
